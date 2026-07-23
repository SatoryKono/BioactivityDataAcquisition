"""Constructor context helpers for publication transformers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from bioetl.application.pipelines.common.transformer_initialization import (
    build_runtime_transformer_init,
    transformer_init_kwargs,
)

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


def publication_transformer_kwargs(
    init_locals: Mapping[str, object],
) -> dict[str, object]:
    """Extract common BasePublicationTransformer kwargs from subclass locals."""
    return transformer_init_kwargs(init_locals)


def coerce_publication_transformer_init(
    init: BasePublicationTransformerContext | str | None,
    /,
    *,
    default_provider: str | None = None,
    default_entity_type: str = "publication",
    **fields: object,
) -> BasePublicationTransformerContext:
    """Normalize compact and legacy constructor styles to one typed input.

    Optional DI fields (``provider``, ``tracer``, filters, strategies, ...) are
    accepted via ``**fields`` to keep this surface under the Sonar S107 budget.
    """
    if isinstance(init, BasePublicationTransformerContext):
        unexpected = ", ".join(
            sorted(key for key, value in fields.items() if value is not None)
        )
        if unexpected:
            raise TypeError(
                "BasePublicationTransformer received unexpected explicit arguments "
                f"with init spec: {unexpected}"
            )
        return init

    provider = fields.get("provider")
    resolved_provider = init if isinstance(init, str) else provider or default_provider
    if not isinstance(resolved_provider, str) or not resolved_provider:
        raise TypeError(
            "BasePublicationTransformer requires a provider string or "
            "BasePublicationTransformerContext."
        )

    entity_type = fields.get("entity_type")
    return BasePublicationTransformerContext(
        provider=resolved_provider,
        entity_type=cast(str, entity_type or default_entity_type),
        silver_filters=cast("SilverFilterConfig | None", fields.get("silver_filters")),
        gold_filters=cast("GoldFilterConfig | None", fields.get("gold_filters")),
        tracer=cast("TracingPort | None", fields.get("tracer")),
        metrics=cast("MetricsPort | None", fields.get("metrics")),
        identity_service=cast(
            "EntityIdentityGenerator | None",
            fields.get("identity_service"),
        ),
        pii_hasher=cast("PiiHasherPort | None", fields.get("pii_hasher")),
        dependencies=cast(
            "TransformerDependencyContext | None",
            fields.get("dependencies"),
        ),
        data_extractor=cast(
            "DataExtractorStrategy | None",
            fields.get("data_extractor"),
        ),
        identifier_resolver=cast(
            "IdentifierResolverStrategy | None",
            fields.get("identifier_resolver"),
        ),
        metadata_strategy=cast(
            "PublicationMetadataStrategy | None",
            fields.get("metadata_strategy"),
        ),
        record_normalizer=cast(
            "RecordNormalizationProcessor | None",
            fields.get("record_normalizer"),
        ),
    )


def build_runtime_publication_transformer_init(
    *,
    default_provider: str,
    default_entity_type: str = "publication",
    owner_type: type[object] | None = None,
) -> object:
    """Return a shared runtime ``__init__`` for thin publication transformers.

    The returned method preserves an explicit DI signature for architecture
    checks while avoiding duplicated constructor bodies in provider modules.
    """
    _runtime_init = build_runtime_transformer_init(
        default_provider,
        default_entity_type,
        owner_type=owner_type,
    )
    _runtime_init.__doc__ = (
        "Shared runtime-generated publication transformer constructor."
    )
    return _runtime_init


__all__ = [
    "BasePublicationTransformerContext",
    "build_runtime_publication_transformer_init",
    "build_runtime_transformer_init",
    "coerce_publication_transformer_init",
    "publication_transformer_kwargs",
]
