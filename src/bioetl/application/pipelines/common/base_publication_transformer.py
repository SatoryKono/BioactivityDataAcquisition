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

from dataclasses import dataclass
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
    build_publication_type_classification_payload,
)

if TYPE_CHECKING:
    from bioetl.domain.behavior import EntityIdentityGenerator
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.entities.base import BaseEntity
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.ports import (
        DataExtractorStrategy,
        IdentifierResolverStrategy,
        MetricsPort,
        PiiHasherPort,
        PublicationMetadataStrategy,
        TracingPort,
    )
    from bioetl.domain.types import BronzeRecord, JsonDict, PrimaryId, SilverRecord


@dataclass(frozen=True, slots=True)
class BasePublicationTransformerContext:
    """Typed constructor input for publication transformer wiring."""

    provider: str
    entity_type: str = "publication"
    silver_filters: SilverFilterConfig | None = None
    gold_filters: GoldFilterConfig | None = None
    tracer: TracingPort | None = None
    metrics: MetricsPort | None = None
    identity_service: EntityIdentityGenerator | None = None
    pii_hasher: PiiHasherPort | None = None
    dependencies: TransformerDependencyContext | None = None
    data_extractor: DataExtractorStrategy | None = None
    identifier_resolver: IdentifierResolverStrategy | None = None
    metadata_strategy: PublicationMetadataStrategy | None = None
    record_normalizer: RecordNormalizationProcessor | None = None


def _coerce_publication_transformer_init(
    init: BasePublicationTransformerContext | str | None,
    /,
    **kwargs: object,
) -> BasePublicationTransformerContext:
    """Normalize compact and legacy constructor styles to one typed input."""
    if isinstance(init, BasePublicationTransformerContext):
        if kwargs:
            unexpected = ", ".join(sorted(kwargs))
            raise TypeError(
                "BasePublicationTransformer received unexpected keyword arguments "
                f"with init spec: {unexpected}"
            )
        return init

    provider = init if isinstance(init, str) else kwargs.pop("provider", None)
    if not isinstance(provider, str) or not provider:
        raise TypeError(
            "BasePublicationTransformer requires a provider string or "
            "BasePublicationTransformerContext."
        )

    unexpected_keys = sorted(
        kwargs.keys()
        - {
            "entity_type",
            "silver_filters",
            "gold_filters",
            "tracer",
            "metrics",
            "identity_service",
            "pii_hasher",
            "dependencies",
            "data_extractor",
            "identifier_resolver",
            "metadata_strategy",
            "record_normalizer",
        }
    )
    if unexpected_keys:
        unexpected_args = ", ".join(unexpected_keys)
        raise TypeError(
            "BasePublicationTransformer received unexpected keyword arguments: "
            f"{unexpected_args}"
        )

    return BasePublicationTransformerContext(
        provider=provider,
        entity_type=cast(str, kwargs.pop("entity_type", "publication")),
        silver_filters=cast(
            "SilverFilterConfig | None", kwargs.pop("silver_filters", None)
        ),
        gold_filters=cast("GoldFilterConfig | None", kwargs.pop("gold_filters", None)),
        tracer=cast("TracingPort | None", kwargs.pop("tracer", None)),
        metrics=cast("MetricsPort | None", kwargs.pop("metrics", None)),
        identity_service=cast(
            "EntityIdentityGenerator | None",
            kwargs.pop("identity_service", None),
        ),
        pii_hasher=cast("PiiHasherPort | None", kwargs.pop("pii_hasher", None)),
        dependencies=cast(
            "TransformerDependencyContext | None",
            kwargs.pop("dependencies", None),
        ),
        data_extractor=cast(
            "DataExtractorStrategy | None",
            kwargs.pop("data_extractor", None),
        ),
        identifier_resolver=cast(
            "IdentifierResolverStrategy | None",
            kwargs.pop("identifier_resolver", None),
        ),
        metadata_strategy=cast(
            "PublicationMetadataStrategy | None",
            kwargs.pop("metadata_strategy", None),
        ),
        record_normalizer=cast(
            "RecordNormalizationProcessor | None",
            kwargs.pop("record_normalizer", None),
        ),
    )


def _classification_payload(
    provider: str,
    raw_type: str | None,
    raw_types_list: list[str] | None,
) -> dict[str, str | None]:
    """Build the normalized publication-type classification payload."""
    return build_publication_type_classification_payload(
        provider,
        raw_type=raw_type,
        raw_types_list=raw_types_list,
        raw_field_name="publication_type",
    )


def _resolve_publication_entity_id(
    transformer: BasePublicationTransformer,
    primary_id_field: str,
    primary_id: PrimaryId,
) -> str:
    """Resolve the stable entity identifier from the validated primary ID."""
    return cast(
        str,
        transformer.compute_entity_id(
            source_id=primary_id,
            record={primary_id_field: primary_id},
        ),
    )


def _prepare_content_hash_payload(business_data: JsonDict) -> JsonDict:
    """Prepare the hash-ready business payload without orchestration metadata."""
    return {
        key: value for key, value in business_data.items() if not key.startswith("_")
    }


def _compute_identifiers(
    transformer: BasePublicationTransformer,
    primary_id_field: str,
    primary_id: PrimaryId,
    business_data: JsonDict,
) -> tuple[str, str]:
    """Compute the stable entity id plus content digest."""
    entity_id = _resolve_publication_entity_id(
        transformer,
        primary_id_field,
        primary_id,
    )
    content_hash = transformer.compute_content_hash(
        _prepare_content_hash_payload(business_data),
        exclude_none=True,
    )
    return entity_id, content_hash


def _build_pre_silver_publication_record(
    transformer: BasePublicationTransformer,
    prepared: PreparedPublicationOutcome,
) -> PreSilverRecord:
    """Build the staged pre-silver publication payload for downstream finalization."""
    entity_id = _resolve_publication_entity_id(
        transformer,
        prepared.primary_id_field,
        prepared.primary_id,
    )
    return PreSilverRecord(
        entity_id=entity_id,
        business_data=prepared.business_data,
        build_silver_record=partial(
            build_publication_silver_record,
            transformer,
        ),
        apply_structural_policy=transformer._apply_structural_policy,
        apply_silver_filter=transformer._apply_silver_filter,
    )


def _assemble_publication_silver_record(
    transformer: BasePublicationTransformer,
    context: PipelineContext,
    *,
    index: int,
    prepared: PreparedPublicationOutcome,
    normalized_business_data: JsonDict,
) -> SilverRecord:
    """Assemble the final Silver record from normalized publication business data."""
    entity_id, content_hash = _compute_identifiers(
        transformer,
        prepared.primary_id_field,
        prepared.primary_id,
        normalized_business_data,
    )
    silver_record = build_publication_silver_record(
        transformer,
        context,
        entity_id,
        content_hash,
        index,
        normalized_business_data,
    )
    return cast(
        "SilverRecord",
        transformer._record_normalizer.project_normalization_findings(
            cast("JsonDict", silver_record),
            context=context,
            index=index,
        ),
    )


class BasePublicationTransformer(BaseTransformer):  # type: ignore[misc]
    """Shared facade flow for publication transformers."""

    def __init__(
        self,
        init: BasePublicationTransformerContext | str | None = None,
        /,
        **kwargs: object,
    ) -> None:
        """Initialize publication transformer with explicit DI seams."""
        resolved = _coerce_publication_transformer_init(init, **kwargs)
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
        if prepared is None:
            return None
        return _build_pre_silver_publication_record(self, prepared)

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
        normalized_business_data = normalize_publication_business_data(
            self, prepared.business_data
        )
        return _assemble_publication_silver_record(
            self,
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
