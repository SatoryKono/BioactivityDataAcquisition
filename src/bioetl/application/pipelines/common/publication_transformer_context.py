"""Constructor context helpers for publication transformers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

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


def coerce_publication_transformer_init(
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


__all__ = [
    "BasePublicationTransformerContext",
    "coerce_publication_transformer_init",
]
