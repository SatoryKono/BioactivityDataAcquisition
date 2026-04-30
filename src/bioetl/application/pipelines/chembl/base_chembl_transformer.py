"""Base ChEMBL Transformer.

Provides common transformation logic for all ChEMBL entity transformers.
Implements Template Method pattern to eliminate duplication across:
- ActivityTransformer
- AssayTransformer
- PublicationTransformer
- MoleculeTransformer
- TargetTransformer
- TargetComponentTransformer
"""

from __future__ import annotations

from bioetl.domain.types import JsonDict

__all__ = ["BaseChemblTransformer"]


from abc import abstractmethod
from typing import TYPE_CHECKING, ClassVar, cast

from bioetl.application.core.base_transformer import (
    BaseTransformer,
    TransformerDependencyContext,
)
from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.entities import BaseEntity
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.ports import MetricsPort, PiiHasherPort, TracingPort
    from bioetl.domain.services import EntityIdentityGenerator
    from bioetl.domain.types import BronzeRecord, PrimaryId, SilverRecord


class BaseChemblTransformer(BaseTransformer):
    """Base class for all ChEMBL transformers.

    Provides common field extraction and mapping logic.
    Implements Template Method pattern for unified transformation flow.

    Subclasses MUST define:
    - `entity_class`: The domain entity class to create
    - `primary_id_field`: Field name of the primary identifier

    Subclasses MUST implement:
    - `_extract_business_data()`: Entity-specific field extraction

    Example:
        >>> class ActivityTransformer(BaseChemblTransformer):
        ...     entity_class = Activity
        ...     primary_id_field = "activity_id"
        ...
        ...     def _extract_business_data(self, record, primary_id):
        ...         return {"activity_id": str(primary_id), ...}

    """

    # Class variables that subclasses must override
    entity_class: ClassVar[type[BaseEntity]]
    primary_id_field: ClassVar[str]

    def __init__(
        self,
        provider: str = "chembl",
        entity_type: str | None = None,
        silver_filters: SilverFilterConfig | None = None,
        gold_filters: GoldFilterConfig | None = None,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        identity_service: EntityIdentityGenerator | None = None,
        pii_hasher: PiiHasherPort | None = None,
        dependencies: TransformerDependencyContext | None = None,
    ) -> None:
        """Initialize ChEMBL transformer.

        Args:
            provider: Data provider identifier. Defaults to 'chembl'.
            entity_type: Entity type for metrics labels. If None, derived from
                entity_class name (e.g., Activity → "activity").
            tracer: Optional tracing port for distributed tracing (O1 observability).
            metrics: Optional metrics port for duration/error tracking (O1 observability).
            silver_filters: Optional domain-level filter configuration for Silver layer.
            gold_filters: Optional filter configuration for Gold layer.
            identity_service: Service for computing entity IDs and content hashes.
            pii_hasher: Optional PII hasher for hashing author names (RULES.md §5.4).
            data_normalizer: Data normalization service for text normalization
                (DOI, PMID, authors, HTML). Defaults to DefaultDataNormalizer.
            contract_policy: Optional pipeline contract policy for field renaming
                and hash include/exclude rules.

        """
        # Derive entity_type from entity_class if not provided
        resolved_entity_type = entity_type
        if resolved_entity_type is None and hasattr(self, "entity_class"):
            resolved_entity_type = self.entity_class.__name__.lower()

        super().__init__(
            provider,
            entity_type=resolved_entity_type,
            silver_filters=silver_filters,
            gold_filters=gold_filters,
            tracer=tracer,
            metrics=metrics,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            dependencies=dependencies,
        )

    def _resolve_primary_id(self, record: BronzeRecord) -> PrimaryId:
        """Resolve the primary identifier from one bronze record."""
        return cast(
            "PrimaryId",
            self._get_required_field(record, self.primary_id_field),
        )

    def _prepare_record(
        self,
        record: BronzeRecord,
    ) -> BronzeRecord:
        """Normalize record aliases before primary-key resolution."""
        return record

    async def transform_pre_silver(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> PreSilverRecord | None:
        """Build an intermediate ChEMBL payload for application finalization."""
        record = self._prepare_record(record)
        primary_id = self._resolve_primary_id(record)
        entity_id = self.compute_entity_id(
            source_id=str(primary_id),
            record={self.primary_id_field: str(primary_id)},
        )
        business_data = self._extract_business_data(record, primary_id)
        return PreSilverRecord(
            entity_id=entity_id,
            business_data=business_data,
            build_silver_record=self._build_pre_silver_json_record,
            apply_structural_policy=self._apply_pre_silver_structural_policy,
            apply_silver_filter=self._apply_pre_silver_filter,
        )

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Template method implementing common ChEMBL transformation flow."""
        record = self._prepare_record(record)
        primary_id = self._resolve_primary_id(record)
        entity_id = self.compute_entity_id(
            source_id=str(primary_id),
            record={self.primary_id_field: str(primary_id)},
        )
        business_data = self._extract_business_data(record, primary_id)
        normalizer = RecordNormalizationProcessor(
            provider=self.provider,
            entity_type=self.entity_type,
        )
        normalized_business_data = normalizer.normalize_business_data(business_data)
        content_hash = self.compute_content_hash(
            normalized_business_data,
            exclude_none=True,
        )
        silver_record = _build_chembl_silver_record(
            self,
            context,
            entity_id,
            content_hash,
            index,
            normalized_business_data,
        )
        return cast(
            "SilverRecord",
            normalizer.project_normalization_findings(
                cast(JsonDict, silver_record),
                context=context,
                index=index,
            ),
        )

    def _build_pre_silver_json_record(
        self,
        context: PipelineContext,
        entity_id: str,
        content_hash: str,
        index: int,
        business_data: JsonDict,
    ) -> JsonDict:
        """Adapt finalized Silver-record construction to the PreSilverRecord protocol."""
        return cast(
            JsonDict,
            _build_chembl_silver_record(
                self,
                context,
                entity_id,
                content_hash,
                index,
                business_data,
            ),
        )

    def _apply_pre_silver_structural_policy(
        self,
        context: PipelineContext,
        record: JsonDict,
        index: int,
    ) -> JsonDict | None:
        """Adapt structural policy application to the PreSilverRecord protocol."""
        return cast(
            JsonDict | None,
            self._apply_structural_policy(
                context,
                cast("SilverRecord", record),
                index,
            ),
        )

    def _apply_pre_silver_filter(
        self,
        context: PipelineContext,
        record: JsonDict,
        index: int,
    ) -> None:
        """Adapt silver-filter application to the PreSilverRecord protocol."""
        self._apply_silver_filter(
            context,
            cast("SilverRecord", record),
            index,
        )

    @abstractmethod
    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: PrimaryId,
    ) -> JsonDict:  # Any: transformer record has heterogeneous values
        """Extract business data from the bronze record.

        Subclasses MUST implement this method to extract entity-specific fields.
        The primary_id is already validated and passed for convenience.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated primary identifier value.

        Returns:
            Dictionary of business data fields for entity creation.

        Example:
            >>> def _extract_business_data(self, record, primary_id):
            ...     return {
            ...         "activity_id": str(primary_id),
            ...         "molecule_chembl_id": record.get("molecule_chembl_id"),
            ...         ...
            ...     }

        """
        ...


def _build_chembl_silver_record(
    transformer: BaseChemblTransformer,
    context: PipelineContext,
    entity_id: str,
    content_hash: str,
    index: int,
    business_data: JsonDict,
) -> SilverRecord:
    """Build a finalized Silver record from normalized ChEMBL business data."""
    entity = transformer._create_entity(
        transformer.entity_class,
        context,
        entity_id=entity_id,
        content_hash=content_hash,
        index=index,
        **business_data,
    )
    return cast("SilverRecord", transformer.entity_to_silver_record(entity))
