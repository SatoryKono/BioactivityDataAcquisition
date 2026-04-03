"""Base Publication Transformer with Template Method pattern.

Provides common transformation flow for publication entities from
different providers (OpenAlex, SemanticScholar, CrossRef).

Reduces code duplication by extracting shared logic:
- Business data extraction orchestration
- Primary ID validation
- Fallback lookup logging
- Entity ID and content hash computation
- Domain entity creation and Silver record conversion
"""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import (
    BaseTransformer,
    TransformerDependencyContext,
)
from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.application.pipelines.common.publication_assembly import (
    PreparedPublicationOutcome,
    build_publication_silver_record,
    normalize_publication_business_data,
    prepare_publication_payload,
)
from bioetl.domain.mapping.publication_type_classification import (
    classify_publication_type,
)

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.entities import BaseEntity
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.ports import (
        DataExtractorStrategy,
        IdentifierResolverStrategy,
        MetricsPort,
        PiiHasherPort,
        PublicationMetadataStrategy,
        TracingPort,
    )
    from bioetl.domain.services import IdentityService
    from bioetl.domain.types import BronzeRecord, JsonDict, SilverRecord


def _classification_payload(
    provider: str,
    raw_type: str | None,
    raw_types_list: list[str] | None,
) -> dict[str, str | None]:
    """Build the normalized publication-type classification payload."""
    entry = classify_publication_type(
        provider,
        raw_type=raw_type,
        raw_types_list=raw_types_list,
    )
    if entry is None:
        return {
            "publication_type_unified": None,
            "publication_subclass": None,
            "publication_class": None,
        }
    return {
        "publication_type_unified": entry.unified_type,
        "publication_subclass": entry.subclass,
        "publication_class": entry.class_code,
    }


class BasePublicationTransformer(BaseTransformer):
    """Shared facade flow for publication transformers.

    Orchestrates execution of injected strategies:
    - DataExtractorStrategy: Extracts business fields from Bronze.
    - IdentifierResolverStrategy: Validates the primary ID.
    - PublicationMetadataStrategy: Provides domain entity classes.
    """

    def __init__(
        self,
        provider: str,
        entity_type: str = "publication",
        silver_filters: SilverFilterConfig | None = None,
        gold_filters: GoldFilterConfig | None = None,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        dependencies: TransformerDependencyContext | None = None,
        data_extractor: DataExtractorStrategy | None = None,
        identifier_resolver: IdentifierResolverStrategy | None = None,
        metadata_strategy: PublicationMetadataStrategy | None = None,
        record_normalizer: RecordNormalizationProcessor | None = None,
    ) -> None:
        """Initialize publication transformer with explicit DI seams."""
        super().__init__(
            provider=provider,
            entity_type=entity_type,
            silver_filters=silver_filters,
            gold_filters=gold_filters,
            tracer=tracer,
            metrics=metrics,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            dependencies=dependencies,
        )
        # Fallback to self if strategies are not provided (legacy subclass support)
        self._data_extractor = data_extractor or cast("DataExtractorStrategy", self)
        self._identifier_resolver = identifier_resolver or cast("IdentifierResolverStrategy", self)
        self._metadata_strategy = metadata_strategy or cast("PublicationMetadataStrategy", self)
        self._record_normalizer = record_normalizer or RecordNormalizationProcessor(
            provider=provider
        )

    # =========================================================================
    # Strategy Interface Implementations (Fallback to legacy subclass methods)
    # =========================================================================

    def pre_extract_validation(self, context: PipelineContext, record: BronzeRecord, index: int) -> None:
        self._pre_extract_validation(context, record, index)

    def extract_business_data(self, record: BronzeRecord) -> JsonDict:
        return self._extract_business_data(record)

    def get_primary_id_field(self) -> str:
        return self._get_primary_id_field()

    def validate_primary_id(
        self,
        context: PipelineContext,
        business_data: JsonDict,
        index: int,
    ) -> tuple[str, Any] | None:  # Any: primary ID values remain provider-specific scalars at the strategy seam.
        return self._validate_primary_id(context, business_data, index)

    def get_entity_class(self) -> type[BaseEntity]:
        return self._get_entity_class()

    def should_log_fallback_lookup(self) -> bool:
        return self._should_log_fallback_lookup()

    # =========================================================================
    # Legacy Protected Methods (For backward compatibility with subclasses)
    # =========================================================================

    def _pre_extract_validation(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> None:
        """Optional pre-extraction validation hook."""
        pass

    def _extract_business_data(self, record: BronzeRecord) -> JsonDict:
        """Extract and normalize fields from bronze record."""
        blocks = getattr(self, "extraction_blocks", [])
        if blocks:
            result: JsonDict = {}
            for block in blocks:
                result.update(block.extract(record))
            return result

        raise NotImplementedError(
            f"{self.__class__.__name__} must implement extraction_blocks property "
            "or override _extract_business_data() method."
        )

    def _get_primary_id_field(self) -> str:
        """Return the name of the primary identifier field."""
        raise NotImplementedError()

    def _get_entity_class(self) -> type[BaseEntity]:
        """Return the domain entity class for this publication type."""
        raise NotImplementedError()

    def _should_log_fallback_lookup(self) -> bool:
        """Return True if fallback lookup logging is enabled."""
        return True

    def _validate_primary_id(
        self,
        context: PipelineContext,
        business_data: JsonDict,
        index: int,
    ) -> tuple[str, Any] | None:  # Any: primary ID values remain provider-specific scalars at the publication boundary.
        """Validate primary ID presence."""
        primary_id_field = self._get_primary_id_field()
        primary_id = business_data.get(primary_id_field)
        if not primary_id:
            context.logger.warning(
                "record_skipped_no_id",
                index=index,
                lookup_method=business_data.get("_lookup_method"),
            )
            return None
        return primary_id_field, primary_id

    _CONTENT_FIELDS: tuple[str, ...] = ("abstract",)
    """Fields to normalize via ``strip_html_tags`` after extraction."""

    def _normalize_content_fields(
        self,
        business_data: dict[
            str, Any  # Any: transformer record has heterogeneous values
        ],  # Any: transformer record has heterogeneous values
    ) -> JsonDict:  # Any: transformer record has heterogeneous values
        """Apply uniform content normalization to text fields.

        Strips residual HTML/XML tags from abstract (and other fields
        listed in ``_CONTENT_FIELDS``).
        The operation is idempotent — safe for providers that already
        clean these fields in ``_extract_business_data``.

        Subclasses MAY override to customize or extend normalization.

        Args:
            business_data: Extracted business data dictionary (mutated in-place).

        Returns:
            The same dictionary with content fields normalized.

        """
        for field in self._CONTENT_FIELDS:
            raw = business_data.get(field)
            if raw is not None:
                business_data[field] = self._data_normalizer.strip_html_tags(raw)
        return business_data

    def _log_fallback_if_needed(
        self,
        context: PipelineContext,
        business_data: JsonDict,
        primary_id_field: str,
        primary_id: Any,  # Any: heterogeneous ID types across providers
    ) -> None:
        """Log fallback lookup usage when applicable."""
        if self._metadata_strategy.should_log_fallback_lookup():
            lookup_method = business_data.get("_lookup_method", "unknown")
            if lookup_method in ("title_fallback", "title_only"):
                context.logger.info(
                    "fallback_lookup_used",
                    **{primary_id_field: primary_id},
                    lookup_method=lookup_method,
                    original_id=business_data.get("_original_id"),
                )

    def _compute_identifiers(
        self,
        primary_id_field: str,
        primary_id: Any,  # Any: heterogeneous ID types across providers
        business_data: JsonDict,
    ) -> tuple[str, str]:
        """Compute entity_id and content_hash.

        Returns:
            Tuple of (entity_id, content_hash).

        """
        entity_id = self._resolve_publication_entity_id(
            primary_id_field,
            primary_id,
        )
        hash_data = self._prepare_content_hash_payload(business_data)
        content_hash = self.compute_content_hash(hash_data, exclude_none=True)
        return entity_id, content_hash

    def _resolve_publication_entity_id(
        self,
        primary_id_field: str,
        primary_id: Any,  # Any: heterogeneous ID types across providers
    ) -> str:
        """Resolve the stable entity identifier from the validated primary ID."""
        return cast(
            str,
            self.compute_entity_id(
                source_id=primary_id,
                record={primary_id_field: primary_id},
            ),
        )

    def _prepare_content_hash_payload(
        self,
        business_data: JsonDict,
    ) -> JsonDict:
        """Prepare the hash-ready business payload without orchestration metadata."""
        return {
            key: value
            for key, value in business_data.items()
            if not key.startswith("_")
        }

    def _normalize_business_data_for_silver_record(
        self,
        business_data: JsonDict,
    ) -> JsonDict:
        """Apply the final normalization boundary before Silver assembly."""
        return normalize_publication_business_data(self, business_data)

    def _build_pre_silver_publication_record(
        self,
        prepared: PreparedPublicationOutcome,
    ) -> PreSilverRecord:
        """Build the staged pre-silver publication payload for downstream finalization."""
        entity_id = self._resolve_publication_entity_id(
            prepared.primary_id_field,
            prepared.primary_id,
        )
        return PreSilverRecord(
            entity_id=entity_id,
            business_data=prepared.business_data,
            build_silver_record=partial(
                build_publication_silver_record,
                self,
            ),
            apply_structural_policy=self._apply_structural_policy,
            apply_silver_filter=self._apply_silver_filter,
        )

    def _assemble_publication_silver_record(
        self,
        context: PipelineContext,
        *,
        index: int,
        prepared: PreparedPublicationOutcome,
        normalized_business_data: JsonDict,
    ) -> SilverRecord:
        """Assemble the final Silver record from normalized publication business data."""
        entity_id, content_hash = self._compute_identifiers(
            prepared.primary_id_field,
            prepared.primary_id,
            normalized_business_data,
        )
        return build_publication_silver_record(
            self,
            context,
            entity_id,
            content_hash,
            index,
            normalized_business_data,
        )

    async def transform_pre_silver(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> PreSilverRecord | None:
        """Build an intermediate publication payload for application finalization."""
        prepared = prepare_publication_payload(self, context, record, index)
        if prepared is None:
            return None
        return self._build_pre_silver_publication_record(prepared)

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Unified publication transformation flow (Facade execution)."""
        prepared = prepare_publication_payload(self, context, record, index)
        if prepared is None:
            return None
        normalized_business_data = self._normalize_business_data_for_silver_record(
            prepared.business_data
        )
        return self._assemble_publication_silver_record(
            context,
            index=index,
            prepared=prepared,
            normalized_business_data=normalized_business_data,
        )

    def _classify_publication_type(
        self,
        provider: str,
        raw_type: str | None = None,
        raw_types_list: list[str] | None = None,
    ) -> dict[str, str | None]:
        """Classify publication type using the unified 3-level hierarchy."""
        return _classification_payload(provider, raw_type, raw_types_list)
