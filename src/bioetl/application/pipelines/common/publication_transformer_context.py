"""Constructor context helpers for publication transformers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from bioetl.application.core.base_transformer import TransformerDependencyContext
    from bioetl.application.core.record_normalization_processor import (
        RecordNormalizationProcessor,
    )
    from bioetl.domain.behavior import EntityIdentityGenerator
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.ports import (
        DataExtractorStrategy,
        IdentifierResolverStrategy,
        MetricsPort,
        PiiHasherPort,
        PublicationMetadataStrategy,
        TracingPort,
    )


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


_PUBLICATION_TRANSFORMER_KWARGS = (
    "entity_type",
    "silver_filters",
    "gold_filters",
    "tracer",
    "metrics",
    "identity_service",
    "pii_hasher",
    "dependencies",
)


def publication_transformer_kwargs(
    init_locals: Mapping[str, object],
) -> dict[str, object]:
    """Extract common BasePublicationTransformer kwargs from subclass locals."""
    return {key: init_locals[key] for key in _PUBLICATION_TRANSFORMER_KWARGS}


def coerce_publication_transformer_init(
    init: BasePublicationTransformerContext | str | None,
    /,
    *,
    provider: str | None = None,
    default_provider: str | None = None,
    entity_type: str | None = None,
    default_entity_type: str = "publication",
    silver_filters: object = None,
    gold_filters: object = None,
    tracer: object = None,
    metrics: object = None,
    identity_service: object = None,
    pii_hasher: object = None,
    dependencies: object = None,
    data_extractor: object = None,
    identifier_resolver: object = None,
    metadata_strategy: object = None,
    record_normalizer: object = None,
) -> BasePublicationTransformerContext:
    """Normalize compact and legacy constructor styles to one typed input."""
    if isinstance(init, BasePublicationTransformerContext):
        explicit_args = {
            "provider": provider,
            "entity_type": entity_type,
            "silver_filters": silver_filters,
            "gold_filters": gold_filters,
            "tracer": tracer,
            "metrics": metrics,
            "identity_service": identity_service,
            "pii_hasher": pii_hasher,
            "dependencies": dependencies,
            "data_extractor": data_extractor,
            "identifier_resolver": identifier_resolver,
            "metadata_strategy": metadata_strategy,
            "record_normalizer": record_normalizer,
        }
        unexpected = ", ".join(
            sorted(key for key, value in explicit_args.items() if value is not None)
        )
        if unexpected:
            raise TypeError(
                "BasePublicationTransformer received unexpected explicit arguments "
                f"with init spec: {unexpected}"
            )
        return init

    resolved_provider = init if isinstance(init, str) else provider or default_provider
    if not isinstance(resolved_provider, str) or not resolved_provider:
        raise TypeError(
            "BasePublicationTransformer requires a provider string or "
            "BasePublicationTransformerContext."
        )

    return BasePublicationTransformerContext(
        provider=resolved_provider,
        entity_type=cast(str, entity_type or default_entity_type),
        silver_filters=cast("SilverFilterConfig | None", silver_filters),
        gold_filters=cast("GoldFilterConfig | None", gold_filters),
        tracer=cast("TracingPort | None", tracer),
        metrics=cast("MetricsPort | None", metrics),
        identity_service=cast(
            "EntityIdentityGenerator | None",
            identity_service,
        ),
        pii_hasher=cast("PiiHasherPort | None", pii_hasher),
        dependencies=cast(
            "TransformerDependencyContext | None",
            dependencies,
        ),
        data_extractor=cast(
            "DataExtractorStrategy | None",
            data_extractor,
        ),
        identifier_resolver=cast(
            "IdentifierResolverStrategy | None",
            identifier_resolver,
        ),
        metadata_strategy=cast(
            "PublicationMetadataStrategy | None",
            metadata_strategy,
        ),
        record_normalizer=cast(
            "RecordNormalizationProcessor | None",
            record_normalizer,
        ),
    )


__all__ = [
    "BasePublicationTransformerContext",
    "coerce_publication_transformer_init",
    "publication_transformer_kwargs",
]
