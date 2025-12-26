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

import json
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, TypeVar

from bioetl.domain.ports import MetricsPort, NoOpMetrics, NoOpTracing, TracingPort
from bioetl.domain.transformations import generate_content_hash

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.entities import BaseEntity
    from bioetl.domain.types import BronzeRecord, ContentHash, SilverRecord

T = TypeVar("T", bound="BaseEntity")


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


class BaseTransformer(ABC):
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

    def __init__(
        self,
        provider: str,
        entity_type: str | None = None,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
    ) -> None:
        """Initialize transformer with provider name and observability.

        Args:
            provider: Data provider identifier (e.g., 'chembl', 'pubchem').
            entity_type: Entity type for metrics labels (e.g., 'activity', 'compound').
            tracer: Tracing port for distributed tracing. Defaults to NoOpTracing.
            metrics: Metrics port for duration/error tracking. Defaults to NoOpMetrics.

        """
        self.provider = provider
        self.entity_type = entity_type or "unknown"
        self._tracer: TracingPort = tracer if tracer is not None else NoOpTracing()
        self._metrics: MetricsPort = metrics if metrics is not None else NoOpMetrics()

    async def transform(
        self,
        context: PipelineContext,
        record: BronzeRecord,
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
            },
        )
        span.__enter__()

        try:
            result = await self._transform_impl(context, record)
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

        Returns:
            SilverRecord if transformation successful, None if record should be skipped.

        Raises:
            TransformationError: If required field is missing.
            ValueError: If entity validation fails.

        """
        ...

    def compute_content_hash(
        self,
        business_data: dict[str, Any],
        *,
        exclude_none: bool = True,
    ) -> ContentHash:
        """Generate canonical content hash for record versioning.

        Implements RULES.md §2.8.1:
        - sha256(provider + canonical_json(record))
        - Normalizes NaN/Inf → null, floats → round(val, 10), dates → ISO

        Args:
            business_data: Business data dictionary (excluding meta fields).
            exclude_none: Whether to exclude None values from hash calculation.

        Returns:
            ContentHash: SHA256 hash of normalized record.

        """
        return generate_content_hash(
            business_data,
            self.provider,
            exclude_none=exclude_none,
        )

    @staticmethod
    def serialize_json(value: Any) -> str | None:
        """Serialize complex values (dict/list) to JSON string.

        Used for storing nested structures in Silver layer as JSON strings.
        - Empty collections ([], {}) are treated as None for semantic consistency
        - Single-element lists are unwrapped: [x] → x
        - Uses sort_keys=True for deterministic output (RULES.md §2.8.1)

        Args:
            value: Value to serialize.

        Returns:
            JSON string for non-empty dict/list, str(value) for other types,
            None for None or empty collections.

        """
        if value is None:
            return None
        if isinstance(value, dict):
            if len(value) == 0:
                return None
            return json.dumps(value, sort_keys=True, ensure_ascii=False)
        if isinstance(value, list):
            if len(value) == 0:
                return None
            # Unwrap single-element lists
            if len(value) == 1:
                item = value[0]
                if isinstance(item, dict):
                    return json.dumps(item, sort_keys=True, ensure_ascii=False)
                return str(item)
            return json.dumps(value, sort_keys=True, ensure_ascii=False)
        return str(value)

    @staticmethod
    def entity_to_silver_record(entity: Any) -> dict[str, Any]:
        """Convert Domain Entity to SilverRecord format.

        Handles lineage fields renaming and formatting:
        - run_id → _run_id (str)
        - run_type → _run_type (str value)
        - source_batch_id → _source_batch_id (str)
        - ingestion_ts → _ingestion_ts (ISO string)

        Args:
            entity: Domain entity with __dict__ attribute.

        Returns:
            SilverRecord dictionary with renamed lineage fields.

        """
        silver_record: dict[str, Any] = entity.__dict__.copy()

        # Handle lineage fields renaming and formatting
        silver_record["_run_id"] = str(silver_record.pop("run_id"))
        silver_record["_run_type"] = str(silver_record.pop("run_type").value)
        silver_record["_source_batch_id"] = str(silver_record.pop("source_batch_id"))
        silver_record["_ingestion_ts"] = silver_record.pop("ingestion_ts").isoformat()

        return silver_record

    # ==================== Helper Methods ====================

    @staticmethod
    def _get_required_field(
        record: BronzeRecord,
        field: str,
        *,
        allow_empty: bool = False,
    ) -> Any:
        """Extract and validate a required field from record.

        Args:
            record: Bronze record dictionary.
            field: Name of the required field.
            allow_empty: If False, empty strings and empty collections raise error.

        Returns:
            Field value if present and valid.

        Raises:
            TransformationError: If field is missing or empty (when allow_empty=False).

        """
        value = record.get(field)
        if value is None:
            raise TransformationError(f"Missing required field: {field}", field=field)

        if not allow_empty:
            # Check for empty strings, lists, dicts
            if isinstance(value, str) and not value.strip():
                raise TransformationError(
                    f"Required field is empty: {field}", field=field
                )
            if isinstance(value, (list, dict)) and len(value) == 0:
                raise TransformationError(
                    f"Required field is empty: {field}", field=field
                )

        return value

    @staticmethod
    def _extract_nested(
        record: BronzeRecord,
        path: str,
        default: Any = None,
    ) -> Any:
        """Safely extract a value from nested dictionaries using dot notation.

        Supports paths like "organism.taxonId" or "proteinDescription.recommendedName.fullName.value".

        Args:
            record: Bronze record dictionary.
            path: Dot-separated path to the nested value (e.g., "a.b.c").
            default: Value to return if path is not found.

        Returns:
            Extracted value or default if path doesn't exist or any intermediate is None.

        Example:
            >>> record = {"organism": {"taxonId": 9606}}
            >>> BaseTransformer._extract_nested(record, "organism.taxonId")
            9606
            >>> BaseTransformer._extract_nested(record, "organism.name", "unknown")
            'unknown'

        """
        keys = path.split(".")
        current = record

        for key in keys:
            if not isinstance(current, dict):
                return default
            current = current.get(key)
            if current is None:
                return default

        return current

    def _create_entity(
        self,
        entity_class: type[T],
        context: PipelineContext,
        entity_id: str,
        content_hash: str,
        **business_data: Any,
    ) -> T:
        """Create a domain entity with lineage metadata.

        Unified entity creation that automatically adds lineage fields
        from the pipeline context.

        Args:
            entity_class: The domain entity class to instantiate.
            context: Pipeline context with run_id, run_type.
            entity_id: Unique entity identifier.
            content_hash: Content hash for versioning.
            **business_data: Entity-specific business data.

        Returns:
            Instantiated domain entity.

        Raises:
            ValueError: If entity validation fails.

        Example:
            >>> entity = self._create_entity(
            ...     Activity,
            ...     context,
            ...     entity_id="chembl:activity:12345",
            ...     content_hash="abc123...",
            ...     activity_id="12345",
            ...     molecule_chembl_id="CHEMBL25",
            ... )

        """
        return entity_class(
            entity_id=entity_id,
            content_hash=content_hash,
            run_id=context.run_id,
            run_type=context.run_type,
            source_batch_id=None,
            **business_data,
        )

    @staticmethod
    def _safe_get(
        record: BronzeRecord,
        field: str,
        default: Any = None,
    ) -> Any:
        """Get a field value with default fallback.

        Simple wrapper around dict.get() for consistency with other helper methods.
        Provided for API completeness alongside _get_required_field().

        Args:
            record: Bronze record dictionary.
            field: Name of the field to extract.
            default: Default value if field is missing or None.

        Returns:
            Field value or default.

        """
        value = record.get(field)
        return value if value is not None else default
