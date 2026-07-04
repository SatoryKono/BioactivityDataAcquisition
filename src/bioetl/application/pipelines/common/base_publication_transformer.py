# mypy: disable-error-code="arg-type,unused-ignore"
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

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import (
    BaseTransformer,
)
from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.application.pipelines.common.publication_assembly import (
    normalize_publication_business_data,
    prepare_publication_payload,
)
from bioetl.application.pipelines.common.publication_transformer_context import (
    BasePublicationTransformerContext,
    coerce_publication_transformer_init,
)
from bioetl.application.pipelines.common.publication_transformer_records import (
    assemble_publication_silver_record,
    build_pre_silver_publication_record,
    classification_payload,
)
from bioetl.application.pipelines.common.publication_vocab_observability import (
    emit_unknown_publication_vocab_metrics,
)
from bioetl.domain.value_objects import PublicationYear

if TYPE_CHECKING:
    from bioetl.application.core.pre_silver_record import PreSilverRecord
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.entities.base import BaseEntity
    from bioetl.domain.ports import (
        DataExtractorStrategy,
        IdentifierResolverStrategy,
        PublicationMetadataStrategy,
    )
    from bioetl.domain.types import BronzeRecord, JsonDict, PrimaryId, SilverRecord


class BasePublicationTransformer(BaseTransformer):  # type: ignore[misc]
    """Shared facade flow for publication transformers."""

    DEFAULT_PROVIDER = ""
    DEFAULT_ENTITY_TYPE = "publication"

    def __init__(
        self,
        init: BasePublicationTransformerContext | str | None = None,
        /,
        **kwargs: Any,  # Any: flexible kwargs forwarding for DI
    ) -> None:
        """Initialize publication transformer with explicit DI seams.

        Optional kwargs:
        - provider: str | None
        - entity_type: str | None
        - silver_filters: SilverFilterConfig | None
        - gold_filters: GoldFilterConfig | None
        - tracer: TracingPort | None
        - metrics: MetricsPort | None
        - identity_service: EntityIdentityGenerator | None
        - pii_hasher: PiiHasherPort | None
        - dependencies: TransformerDependencyContext | None
        - data_extractor: DataExtractorStrategy | None
        - identifier_resolver: IdentifierResolverStrategy | None
        - metadata_strategy: PublicationMetadataStrategy | None
        - record_normalizer: RecordNormalizationProcessor | None
        """
        resolved = coerce_publication_transformer_init(
            init,
            default_provider=self.DEFAULT_PROVIDER,
            default_entity_type=self.DEFAULT_ENTITY_TYPE,
            **kwargs,
        )
        super().__init__(
            provider=resolved.provider,
            entity_type=resolved.entity_type,
            silver_filters=resolved.silver_filters,
            gold_filters=resolved.gold_filters,
            tracer=resolved.tracer,
            metrics=resolved.metrics,
            identity_service=resolved.identity_service,
            pii_hasher=resolved.pii_hasher,
            dependencies=resolved.dependencies,
        )
        # Fallback to self if strategies are not provided (legacy subclass support)
        self._data_extractor = resolved.data_extractor or cast(
            "DataExtractorStrategy",
            self,
        )
        self._identifier_resolver = resolved.identifier_resolver or cast(
            "IdentifierResolverStrategy", self
        )
        self._metadata_strategy = resolved.metadata_strategy or cast(
            "PublicationMetadataStrategy", self
        )
        self._record_normalizer = (
            resolved.record_normalizer
            or RecordNormalizationProcessor(
                provider=resolved.provider,
                entity_type=resolved.entity_type,
            )
        )

    def pre_extract_validation(
        self, context: PipelineContext, record: BronzeRecord, index: int
    ) -> None:
        """Run provider-specific pre-extraction checks for one bronze record."""
        self._pre_extract_validation(context, record, index)

    def extract_business_data(self, record: BronzeRecord) -> JsonDict:
        """Extract normalized publication business fields from a bronze record."""
        return self._extract_business_data(record)

    def get_primary_id_field(self) -> str:
        """Return the provider-specific primary identifier field name."""
        return self._get_primary_id_field()

    def validate_primary_id(
        self,
        context: PipelineContext,
        business_data: JsonDict,
        index: int,
    ) -> tuple[str, PrimaryId] | None:
        """Validate and return primary-id metadata for one publication payload."""
        return self._validate_primary_id(context, business_data, index)

    def get_entity_class(self) -> type[BaseEntity]:
        """Return the domain entity class used for publication inflation."""
        return self._get_entity_class()

    def should_log_fallback_lookup(self) -> bool:
        """Return whether fallback-lookup observability should be emitted."""
        return self._should_log_fallback_lookup()

    def post_process_silver_record(self, silver_record: SilverRecord) -> SilverRecord:
        """Apply the publication post-processing hook expected by assembly helpers.

        Publication assembly still treats the metadata strategy as the last step
        before returning a finalized Silver record. Most publication transformers
        do not need extra work here, so the default behavior is a no-op.
        """
        return self._post_process_silver_record(silver_record)

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

    def _post_process_silver_record(self, silver_record: SilverRecord) -> SilverRecord:
        """Finalize a Silver record after entity inflation.

        Subclasses can override this hook for compatibility-sensitive cleanup,
        but the common publication path should preserve the record unchanged.
        """
        return silver_record

    def _validate_primary_id(
        self,
        context: PipelineContext,
        business_data: JsonDict,
        index: int,
    ) -> tuple[str, PrimaryId] | None:
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

    def _validate_publication_year_value(self, raw: object) -> int | None:
        """Validate publication year and return the canonical integer value."""
        value = self.validate_value_object(
            PublicationYear,
            raw,
            as_string=False,
        )
        return value if isinstance(value, int) else None

    _CONTENT_FIELDS: tuple[str, ...] = ("abstract",)
    """Fields to normalize via ``strip_html_tags`` after extraction."""

    def _normalize_content_fields(
        self,
        business_data: dict[
            str, Any  # Any: transformer record has heterogeneous values
        ],  # Any: transformer record has heterogeneous values
    ) -> JsonDict:  # Any: transformer record has heterogeneous values
        """Apply uniform text cleanup to configured content fields."""
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
        primary_id: PrimaryId,
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

    async def transform_pre_silver(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> PreSilverRecord | None:
        """Build an intermediate publication payload for application finalization."""
        prepared = prepare_publication_payload(self, context, record, index)
        return build_pre_silver_publication_record(self, prepared)

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Unified publication transformation flow (Facade execution)."""
        prepared = prepare_publication_payload(self, context, record, index)
        normalized_business_data = normalize_publication_business_data(
            self, prepared.business_data
        )
        self._emit_unknown_publication_vocab_metrics(
            context,
            normalized_business_data,
        )
        return assemble_publication_silver_record(
            self,
            context,
            index=index,
            prepared=prepared,
            normalized_business_data=normalized_business_data,
        )

    def _emit_unknown_publication_vocab_metrics(
        self,
        context: PipelineContext,
        normalized_business_data: JsonDict,
    ) -> None:
        """Publish bounded counters for unknown raw publication vocabulary drift."""
        pipeline_name = context.pipeline_name or f"{self.provider}_{self.entity_type}"
        emit_unknown_publication_vocab_metrics(
            metrics=self._metrics,
            pipeline_name=pipeline_name,
            provider=self.provider,
            normalized_business_data=normalized_business_data,
        )

    def _classify_publication_type(
        self,
        provider: str,
        raw_type: str | None = None,
        raw_types_list: list[str] | None = None,
    ) -> dict[str, str | None]:
        """Classify publication type using the unified 3-level hierarchy."""
        return classification_payload(provider, raw_type, raw_types_list)
