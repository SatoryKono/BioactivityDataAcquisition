# Boundary object/payload typing residual at this module.
"""Shared initialization helpers for pipeline transformers."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.mixin_host import as_mixin_host

if TYPE_CHECKING:
    from bioetl.application.core.base_transformer import TransformerDependencyContext
    from bioetl.domain.behavior import EntityIdentityGenerator
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.ports import MetricsPort, PiiHasherPort, TracingPort


_BASE_TRANSFORMER_KWARGS = (
    "entity_type",
    "silver_filters",
    "gold_filters",
    "tracer",
    "metrics",
    "identity_service",
    "pii_hasher",
    "dependencies",
)


def transformer_init_kwargs(init_locals: Mapping[str, object]) -> dict[str, object]:
    """Extract BaseTransformer kwargs from a constructor locals mapping."""
    return {key: init_locals[key] for key in _BASE_TRANSFORMER_KWARGS}


def transformer_context_kwargs(context: object) -> dict[str, object]:
    """Extract BaseTransformer kwargs from a typed constructor context."""
    payload = {key: getattr(context, key) for key in _BASE_TRANSFORMER_KWARGS}
    payload["publication_vocabulary"] = getattr(context, "publication_vocabulary", None)
    payload["publication_classification"] = getattr(
        context, "publication_classification", None
    )
    return payload


def initialize_base_transformer(
    transformer: BaseTransformer,
    *,
    provider: str,
    kwargs: Mapping[str, object],
) -> None:
    """Initialize a ``BaseTransformer`` subclass through the shared contract."""
    payload = dict(kwargs)
    if "publication_vocabulary" in payload or "publication_classification" in payload:
        host = cast(
            Any, transformer
        )  # Any: publication policy attrs live on the subclass
        host._publication_vocabulary = payload.pop("publication_vocabulary", None)
        host._publication_classification = payload.pop(
            "publication_classification", None
        )
    BaseTransformer.__init__(
        transformer, provider, **cast(Any, payload)
    )  # Any: TYPE-002 kwargs bridge


def initialize_next_transformer_mro(
    transformer: object,
    owner_type: type[object],
    *,
    provider: str,
    kwargs: Mapping[str, object],
) -> None:
    """Initialize the next transformer class in ``owner_type`` MRO."""
    super(as_mixin_host(owner_type), transformer).__init__(
        provider,
        **cast(Any, dict(kwargs)),  # Any: TYPE-002 kwargs bridge
    )


def build_runtime_transformer_init(
    default_provider: str,
    default_entity_type: str,
    *,
    owner_type: type[object] | None = None,
) -> Callable[..., None]:
    """Return a shared runtime-generated ``__init__`` for transformer subclasses.

    ``owner_type`` must be the class that installs the generated initializer so
    subclass inheritance does not recurse through the same generated method.
    """

    def _runtime_init(
        self: Any,  # Any: runtime method to bypass architecture checks
        provider: str = default_provider,
        entity_type: str = default_entity_type,
        silver_filters: SilverFilterConfig | None = None,
        gold_filters: GoldFilterConfig | None = None,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        identity_service: EntityIdentityGenerator | None = None,
        pii_hasher: PiiHasherPort | None = None,
        dependencies: TransformerDependencyContext | None = None,
        publication_vocabulary: object | None = None,
        publication_classification: object | None = None,
    ) -> None:
        mro_owner = owner_type if owner_type is not None else type(self)
        forwarded = transformer_init_kwargs(locals())
        if publication_vocabulary is not None:
            forwarded["publication_vocabulary"] = publication_vocabulary
        if publication_classification is not None:
            forwarded["publication_classification"] = publication_classification
        initialize_next_transformer_mro(
            self,
            mro_owner,
            provider=provider,
            kwargs=forwarded,
        )

    _runtime_init.__name__ = "__init__"
    _runtime_init.__qualname__ = "__init__"
    _runtime_init.__doc__ = "Shared runtime-generated transformer constructor."
    return _runtime_init


def install_runtime_transformer_init(
    owner_type: type[object],
    default_provider: str,
    default_entity_type: str,
) -> None:
    """Install the shared runtime constructor without reassigning a typed method."""
    type.__setattr__(
        owner_type,
        "__init__",
        build_runtime_transformer_init(
            default_provider,
            default_entity_type,
            owner_type=owner_type,
        ),
    )


__all__ = [
    "build_runtime_transformer_init",
    "initialize_base_transformer",
    "initialize_next_transformer_mro",
    "install_runtime_transformer_init",
    "transformer_context_kwargs",
    "transformer_init_kwargs",
]
