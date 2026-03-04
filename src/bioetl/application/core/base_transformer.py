"""Base Transformer class for Bronze → Silver transformations.

Provides common functionality for all entity transformers:
- Content hash generation (RULES.md §2.8.1)
- JSON serialization of complex fields
- Entity to SilverRecord conversion with lineage field renaming
- Template Method pattern for unified error handling
- Helper methods for field extraction and entity creation
- Tracing and metrics for observability (O1)

Implements DRY principle by extracting shared logic from entity transformers.
"""

from __future__ import annotations

import dataclasses
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, Protocol, TypeVar, runtime_checkable

from bioetl.application.core.base_transformer_helpers_mixin import (
    _BaseTransformerRecordHelpersMixin,
)
from bioetl.domain.ports import (
    DataNormalizationPort,
    MetricsPort,
    NoOpMetrics,
    NoOpPiiHasher,
    NoOpTracing,
    PiiHasherPort,
    TracingPort,
)
from bioetl.domain.services import DataNormalizationService, IdentityService
from bioetl.domain.types import ContentHash, EntityID, GoldRecord

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.entities import BaseEntity
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.types import BronzeRecord, SilverRecord

T = TypeVar("T", bound="BaseEntity")
V = TypeVar("V", covariant=True)


@dataclasses.dataclass(frozen=True)
class _DefaultContractPolicy:
    """Fallback contract policy when none is injected."""

    primary_key: list[str] = dataclasses.field(default_factory=lambda: ["entity_id"])
    merge_keys: list[str] = dataclasses.field(default_factory=lambda: ["entity_id"])
    rename_map: dict[str, str] = dataclasses.field(
        default_factory=lambda: {
            "run_id": "_run_id",
            "run_type": "_run_type",
            "source_batch_id": "_source_batch_id",
            "ingestion_ts": "_ingestion_ts",
            "source": "_source",
        }
    )
    hash_include: list[str] = dataclasses.field(default_factory=list)
    hash_exclude: list[str] = dataclasses.field(
        default_factory=lambda: ["_ingestion_ts", "_run_id", "_run_type"]
    )


@runtime_checkable
class ValueObjectWithFromRaw(Protocol[V]):
    """Protocol for Value Objects with from_raw() class method.

    This protocol enables type-safe usage of validate_value_object()
    with any Value Object class that implements from_raw().
    """

    @classmethod
    def from_raw(cls, raw: Any) -> V | None:  # Any: raw input
        """Create Value Object from raw value, returning None if invalid.

        Args:
            raw: Raw input value.

        Returns:
            New instance constructed from the input.
        """
        ...

    @property
    def value(self) -> Any:  # Any: VO value type varies (str | int | float)
        """Get the internal value."""
        ...


class TransformationError(Exception):
    """Raised when a transformation fails due to missing/invalid data.

    This exception is caught by the Template Method and results in
    skipping the record (returning None) with appropriate logging.
    """

    def __init__(self, message: str, field: str | None = None) -> None:
        """Initialize transformation error.

        Args:
            message: Error description.
            field: Name of the field that caused the error (optional).

        """
        super().__init__(message)
        self.field = field


class FilteredOutError(Exception):
    """Raised when a record is excluded by Silver filters.

    Unlike data-quality failures, this indicates an expected business filter
    decision. Batch processing may route such records to quasi-quarantine
    for traceability.
    """

    def __init__(self, reason: str = "Record excluded by silver filters") -> None:
        """Initialize filtered-out error with human-readable reason."""
        super().__init__(reason)


class BaseTransformer(_BaseTransformerRecordHelpersMixin, ABC):
    """Abstract base class for Bronze → Silver transformers.

    Implements Template Method pattern for unified transformation flow:
    1. Call `_transform_impl()` (abstract hook method)
    2. Handle ValueError and TransformationError with logging
    3. Return None for skipped records

    Provides:
    - `compute_content_hash()`: Canonical content hash generation (RULES.md §2.8.1)
    - `serialize_json()`: JSON serialization for complex fields (dict/list)
    - `entity_to_silver_record()`: Entity → SilverRecord conversion with lineage fields
    - `_get_required_field()`: Extract and validate required fields
    - `_extract_nested()`: Safe extraction of nested dictionary values
    - `_create_entity()`: Unified entity creation with lineage metadata

    Observability (O1):
    - Tracing spans for transform operations
    - Duration histograms by entity_type
    - Error counters by error_type

    Subclasses MUST implement:
    - `_transform_impl()`: Entity-specific transformation logic
    """

    # Fields to exclude from Gold layer (JSON strings retained only in Silver)
    # UPDATED: Empty set to ensure identical columns in Silver and Gold (User Request)
    GOLD_EXCLUDE_FIELDS: ClassVar[frozenset[str]] = frozenset()

    def __init__(
        self,
        provider: str,
        entity_type: str | None = None,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        silver_filters: SilverFilterConfig | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        data_normalizer: DataNormalizationPort | None = None,
        contract_policy: Any = None,  # Any: PipelineContractPolicy (avoids composition import)
    ) -> None:
        """Initialize transformer with provider name and observability.

        Args:
            provider: Data provider identifier (e.g., 'chembl', 'pubchem').
            entity_type: Entity type for metrics labels (e.g., 'activity', 'compound').
            tracer: Tracing port for distributed tracing. Defaults to NoOpTracing.
            metrics: Metrics port for duration/error tracking. Defaults to NoOpMetrics.
            silver_filters: Optional domain-level filter configuration for Silver layer.
                Applied AFTER transformation but BEFORE writing to Silver.
            gold_filters: Optional filter configuration for Gold layer.
            identity_service: Service for computing entity IDs and content hashes.
                Defaults to a new IdentityService instance.
            pii_hasher: Optional PII hasher for hashing author names and other PII.
                Defaults to NoOpPiiHasher (no hashing) for backward compatibility.
            data_normalizer: Data normalization service for text normalization
                (DOI, PMID, authors, HTML). Defaults to DataNormalizationService.

        """
        self.provider = provider
        self.entity_type = entity_type or "unknown"
        self._tracer: TracingPort = tracer if tracer is not None else NoOpTracing()
        self._metrics: MetricsPort = metrics if metrics is not None else NoOpMetrics()
        self._silver_filters = silver_filters
        self._gold_filters = gold_filters
        self._identity: IdentityService = (
            identity_service if identity_service is not None else IdentityService()
        )
        self._pii_hasher: PiiHasherPort = (
            pii_hasher if pii_hasher is not None else NoOpPiiHasher()
        )
        self._data_normalizer: DataNormalizationPort = (
            data_normalizer
            if data_normalizer is not None
            else DataNormalizationService()
        )
        self._contract_policy = (
            contract_policy if contract_policy is not None else _DefaultContractPolicy()
        )

    # ========================================================================
    # PII Hashing Methods (RULES.md §5.4)
    # ========================================================================

    def hash_pii_value(self, value: str | None) -> str | None:
        """Hash a single PII value (e.g., author name).

        Delegates to PiiHasherPort. Uses NoOpPiiHasher by default
        (no hashing) for backward compatibility.

        Args:
            value: PII value to hash, or None.

        Returns:
            Hashed value, or None if input is None.
        """
        return self._pii_hasher.hash_value(value)

    def hash_pii_list(self, values: list[str] | None) -> list[str] | None:
        """Hash a list of PII values (e.g., list of author names).

        Delegates to PiiHasherPort. Uses NoOpPiiHasher by default
        (no hashing) for backward compatibility.

        Args:
            values: List of PII values to hash, or None.

        Returns:
            List of hashed values, or None if input is None.
        """
        return self._pii_hasher.hash_list(values)

    # ========================================================================
    # Value Object Validation Methods (Consolidated Logic)
    # ========================================================================

    @staticmethod
    def validate_value_object(
        vo_class: type[ValueObjectWithFromRaw[Any]],  # Any: generic VO type param
        value: Any,  # Any: raw input from API (str | int | None)
        *,
        as_string: bool = True,
    ) -> str | int | None:
        """Validate a value using a Value Object and return the result.

        Consolidates the common pattern of:
        1. Call VO.from_raw(value)
        2. Return str(vo) if vo else None

        This eliminates repetitive code across transformers.

        Args:
            vo_class: Value Object class with from_raw() class method.
            value: Raw value to validate.
            as_string: If True, return str(vo); if False, return vo.value.

        Returns:
            Validated value as string/int, or None if validation fails.

        Example:
            >>> # Instead of:
            >>> doi_vo = DOI.from_raw(rec.get("doi"))
            >>> doi = str(doi_vo) if doi_vo else None
            >>>
            >>> # Use:
            >>> doi = self.validate_value_object(DOI, rec.get("doi"))

        """
        vo = vo_class.from_raw(value)
        if vo is None:
            return None
        return str(vo) if as_string else vo.value

    @staticmethod
    def validate_value_objects(
        vo_class: type[ValueObjectWithFromRaw[Any]],  # Any: generic VO type param
        values: list[Any] | None,  # Any: raw inputs from API
        *,
        as_string: bool = True,
    ) -> list[str | int] | None:
        """Validate a list of values using a Value Object.

        Useful for fields like taxonomy_id list in target_transformer.

        Args:
            vo_class: Value Object class with from_raw() class method.
            values: List of raw values to validate, or None.
            as_string: If True, return str(vo); if False, return vo.value.

        Returns:
            List of validated values, or None if input is None/empty.

        Example:
            >>> # Instead of:
            >>> validated_tax_ids: list[int] | None = None
            >>> if raw_tax_ids:
            >>>     validated_list: list[int] = []
            >>>     for tid in raw_tax_ids:
            >>>         vo = TaxonomyId.from_raw(tid)
            >>>         if vo is not None:
            >>>             validated_list.append(vo.value)
            >>>     validated_tax_ids = validated_list if validated_list else None
            >>>
            >>> # Use:
            >>> validated_tax_ids = self.validate_value_objects(
            >>>     TaxonomyId, raw_tax_ids, as_string=False
            >>> )

        """
        if not values:
            return None
        result: list[str | int] = []
        for val in values:
            vo = vo_class.from_raw(val)
            if vo is not None:
                result.append(str(vo) if as_string else vo.value)
        return result if result else None

    async def transform(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Transform Bronze record to Silver format (Template Method).

        This is the main entry point implementing Template Method pattern.
        Handles common error handling and logging, delegating actual
        transformation to `_transform_impl()`.

        Observability (O1):
        - Creates tracing span "transform_record" with provider/entity attributes
        - Records transform_duration_seconds histogram by entity_type
        - Increments transform_errors_total counter by error_type on failure

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from data source.
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if record should be skipped.

        """
        start_time = time.perf_counter()
        error_type: str | None = None

        # Start tracing span (always available via NoOpTracing default)
        otel_tracer = self._tracer.get_tracer("bioetl.transformer")
        span = otel_tracer.start_as_current_span(
            "transform_record",
            attributes={
                "bioetl.provider": self.provider,
                "bioetl.entity_type": self.entity_type,
                "bioetl.run_id": str(context.run_id),
                "bioetl.record_index": index,
            },
        )
        span.__enter__()

        try:
            result = await self._transform_impl(context, record, index)
            if result is not None and not self.should_write_silver(
                context,
                result,  # type: ignore[arg-type]  # SilverRecord is dict at runtime
            ):
                context.logger.debug(
                    "silver_filter_excluded",
                    provider=self.provider,
                    entity_type=self.entity_type,
                    record_index=index,
                )
                raise FilteredOutError()
            return result
        except TransformationError as e:
            error_type = "transformation_error"
            context.logger.warning(
                "transformation_skipped",
                reason=str(e),
                field=e.field,
                provider=self.provider,
            )
            span.set_attribute("error", True)
            span.set_attribute("error.type", error_type)
            return None
        except ValueError as e:
            error_type = "validation_error"
            context.logger.warning(
                "entity_validation_failed",
                error=str(e),
                provider=self.provider,
            )
            span.set_attribute("error", True)
            span.set_attribute("error.type", error_type)
            return None
        finally:
            duration = time.perf_counter() - start_time

            # Record duration histogram (always available via NoOpMetrics default)
            self._metrics.observe_histogram(
                "transform_duration_seconds",
                duration,
                labels={
                    "provider": self.provider,
                    "entity_type": self.entity_type,
                },
            )

            # Record error counter if error occurred
            if error_type:
                self._metrics.increment_counter(
                    "transform_errors_total",
                    1,
                    labels={
                        "provider": self.provider,
                        "entity_type": self.entity_type,
                        "error_type": error_type,
                    },
                )

            # End tracing span
            span.set_attribute("bioetl.duration_ms", duration * 1000)
            span.__exit__(None, None, None)

    @abstractmethod
    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Implement entity-specific transformation logic.

        Subclasses MUST implement this method to perform actual transformation:
        1. Extract and validate required fields using `_get_required_field()`
        2. Build business_data dictionary
        3. Generate entity_id and content_hash
        4. Create Domain Entity using `_create_entity()`
        5. Convert to SilverRecord using `entity_to_silver_record()`

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from data source.
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if record should be skipped.

        Raises:
            TransformationError: If required field is missing.
            ValueError: If entity validation fails.

        """
        ...

    def should_write_silver(
        self, _context: PipelineContext, record: GoldRecord
    ) -> bool:
        """Determine if a transformed record should be written to Silver.

        Uses silver_filters from config if configured, otherwise passes all records.
        Applied AFTER transformation but BEFORE writing to Silver layer.

        Args:
            _context: Pipeline context (unused in base implementation).
            record: Transformed record to evaluate.

        Returns:
            True if record passes domain-level silver filters.

        """
        if self._silver_filters is None or self._silver_filters.is_empty():
            return True
        return self._silver_filters.should_include(record)

    def should_write_gold(self, _context: PipelineContext, record: GoldRecord) -> bool:
        """Determine if a Silver record should be written to Gold.

        Uses gold_filters from config if configured, otherwise passes all records.
        Subclasses can override for custom filtering logic.

        Args:
            _context: Pipeline context (unused in base implementation).
            record: Silver record to evaluate.

        Returns:
            True if record should be written to Gold layer.

        """
        if self._gold_filters is None or self._gold_filters.is_empty():
            return True
        return self._gold_filters.should_include(record)

    def transform_for_gold(
        self, _context: PipelineContext, silver_record: GoldRecord
    ) -> GoldRecord:
        """Transform Silver record for Gold layer.

        Removes JSON string fields that are retained only in Silver for forensic purposes.
        Subclasses can override for custom Gold transformations.

        Args:
            _context: Pipeline context (unused in base implementation).
            silver_record: Silver record to transform.

        Returns:
            Record suitable for Gold layer (flat fields only).

        """
        return {
            k: v for k, v in silver_record.items() if k not in self.GOLD_EXCLUDE_FIELDS
        }

    def compute_content_hash(
        self,
        business_data: GoldRecord,
        *,
        exclude_none: bool = True,
    ) -> ContentHash:
        """Generate canonical content hash for record versioning.

        Delegates to IdentityService for computation.

        Implements RULES.md §2.8.1:
        - sha256(provider + canonical_json(record))
        - Normalizes NaN/Inf → null, floats → round(val, 10), dates → ISO

        Args:
            business_data: Business data dictionary (excluding meta fields).
            exclude_none: Whether to exclude None values from hash calculation.

        Returns:
            ContentHash: SHA256 hash of normalized record.

        """
        hash_input = self._apply_hash_policy(business_data)
        return self._identity.compute_content_hash(
            self.provider,
            hash_input,
            exclude_none=exclude_none,
        )

    def compute_entity_id(
        self,
        source_id: str | None,
        record: GoldRecord,
    ) -> EntityID:
        """Generate stable entity identifier.

        Delegates to IdentityService for computation.

        If source_id is provided, uses it for stable identification.
        Otherwise, generates identifier from content hash prefix.

        Args:
            source_id: Source system identifier (e.g., activity_id from API).
            record: Record for fallback hash-based identification.

        Returns:
            EntityID in format "{provider}:{id}" or "{provider}:{hash_prefix}".

        """
        return self._identity.compute_entity_id(
            provider=self.provider,
            entity_type=self.entity_type,
            source_id=source_id,
            record=record,
        )

    def entity_to_silver_record(
        self,
        entity: Any,  # Any: generic domain entity; type varies by pipeline
    ) -> GoldRecord:
        """Convert Domain Entity to SilverRecord format using policy rename map.

        Args:
            entity: Entity.

        Returns:
            Result dictionary.
        """
        silver_record = dataclasses.asdict(entity)

        rename_map = self._contract_policy.rename_map
        for source_key, target_key in rename_map.items():
            if source_key in silver_record and target_key not in silver_record:
                value = silver_record.pop(source_key)
                silver_record[target_key] = self._normalize_lineage_value(
                    source_key, value
                )

        return silver_record

    def _apply_hash_policy(self, business_data: GoldRecord) -> GoldRecord:
        """Apply include/exclude hash policy from contract config."""
        include_fields = self._contract_policy.hash_include
        exclude_fields = set(self._contract_policy.hash_exclude)

        if include_fields:
            scoped = {
                k: business_data.get(k) for k in include_fields if k in business_data
            }
        else:
            scoped = dict(business_data)

        for field in exclude_fields:
            scoped.pop(field, None)

        return scoped
