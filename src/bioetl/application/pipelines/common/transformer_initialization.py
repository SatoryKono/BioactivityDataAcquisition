"""Shared initialization helpers for pipeline transformers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from bioetl.application.core.base_transformer import BaseTransformer

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
    return {key: getattr(context, key) for key in _BASE_TRANSFORMER_KWARGS}


def initialize_base_transformer(
    transformer: BaseTransformer,
    *,
    provider: str,
    kwargs: Mapping[str, object],
) -> None:
    """Initialize a ``BaseTransformer`` subclass through the shared contract."""
    BaseTransformer.__init__(transformer, provider, **dict(kwargs))  # type: ignore[arg-type]


def initialize_next_transformer_mro(
    transformer: object,
    owner_type: type[object],
    *,
    provider: str,
    kwargs: Mapping[str, object],
) -> None:
    """Initialize the next transformer class in ``owner_type`` MRO."""
    super(owner_type, transformer).__init__(provider, **dict(kwargs))  # type: ignore[misc]


def build_runtime_transformer_init(
    default_provider: str,
    default_entity_type: str,
    *,
    owner_type: type[object] | None = None,
) -> object:
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
    ) -> None:
        mro_owner = owner_type if owner_type is not None else type(self)
        initialize_next_transformer_mro(
            self,
            mro_owner,
            provider=provider,
            kwargs=transformer_init_kwargs(locals()),
        )

    _runtime_init.__name__ = "__init__"
    _runtime_init.__qualname__ = "__init__"
    _runtime_init.__doc__ = "Shared runtime-generated transformer constructor."
    return _runtime_init


__all__ = [
    "build_runtime_transformer_init",
    "initialize_base_transformer",
    "initialize_next_transformer_mro",
    "transformer_context_kwargs",
    "transformer_init_kwargs",
]
