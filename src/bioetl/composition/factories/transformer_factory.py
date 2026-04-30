# src/bioetl/composition/factories/transformer_factory.py
"""Factory functions for DI-based transformer creation."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from importlib import import_module
from typing import TYPE_CHECKING, Final

from bioetl.composition.factories._transformer_spec_rows import (
    BUILTIN_TRANSFORMER_SPEC_ROWS,
)
from bioetl.composition.factories.transformer_dependencies import (
    build_transformer_dependencies,
)

if TYPE_CHECKING:
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.application.core.base_transformer.types import (
        TransformerDependencyContext,
    )
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.ports import (
        ContractPolicyProtocol,
        DataNormalizationPort,
        MetricsPort,
        PiiHasherPort,
        TracingPort,
    )
    from bioetl.domain.services import EntityIdentityGenerator

# Mapping of (provider, entity_type) to transformer class
_TRANSFORMER_REGISTRY: dict[tuple[str, str], type[BaseTransformer]] = {}


@dataclass(frozen=True, slots=True)
class TransformerRegistrationSpec:
    """Declarative transformer registration entry."""

    provider: str
    entity_type: str
    module_path: str
    class_name: str


_BUILTIN_TRANSFORMER_SPECS: Final[tuple[TransformerRegistrationSpec, ...]] = tuple(
    TransformerRegistrationSpec(*spec) for spec in BUILTIN_TRANSFORMER_SPEC_ROWS
)


def register_transformer(
    provider: str,
    entity_type: str,
    transformer_class: type[BaseTransformer],
) -> None:
    """Register a transformer class for a provider/entity combination.

    Args:
        provider: Provider name (e.g., 'chembl', 'pubchem').
        entity_type: Entity type (e.g., 'activity', 'compound').
        transformer_class: The transformer class to register.

    """
    _TRANSFORMER_REGISTRY[(provider, entity_type)] = transformer_class


def create_transformer(
    provider: str,
    entity_type: str,
    tracer: TracingPort | None = None,
    metrics: MetricsPort | None = None,
    silver_filters: SilverFilterConfig | None = None,
    gold_filters: GoldFilterConfig | None = None,
    identity_service: EntityIdentityGenerator | None = None,
    pii_hasher: PiiHasherPort | None = None,
    data_normalizer: DataNormalizationPort | None = None,
    contract_policy: ContractPolicyProtocol | None = None,
    dependencies: TransformerDependencyContext | None = None,
) -> BaseTransformer:
    """Create a transformer instance for the given provider and entity type.

    Args:
        provider: Provider name (e.g., 'chembl', 'pubchem').
        entity_type: Entity type (e.g., 'activity', 'compound').
        tracer: Optional tracing port for distributed tracing (O1 observability).
        metrics: Optional metrics port for duration/error tracking (O1 observability).
        silver_filters: Optional domain-level filter configuration for Silver layer.
        gold_filters: Optional filter configuration for Gold layer.
        identity_service: Service for computing entity IDs and content hashes.
        pii_hasher: Optional PII hasher for hashing author names and other PII.
        data_normalizer: Optional data normalization service for text normalization
            (DOI, PMID, authors, HTML).
        contract_policy: Optional pipeline contract policy.
        dependencies: Optional explicit dependency bundle. When omitted,
            composition builds explicit defaults instead of relying on
            BaseTransformer fallbacks.

    Returns:
        Configured transformer instance with observability.

    Raises:
        KeyError: If no transformer is registered for the provider/entity combination.

    """
    key = (provider, entity_type)
    if key not in _TRANSFORMER_REGISTRY:
        raise KeyError(
            f"No transformer registered for provider='{provider}', "
            f"entity_type='{entity_type}'. "
            f"Available: {list(_TRANSFORMER_REGISTRY.keys())}"
        )

    transformer_class = _TRANSFORMER_REGISTRY[key]
    resolved_dependencies = (
        dependencies
        if dependencies is not None
        else build_transformer_dependencies(
            tracer=tracer,
            metrics=metrics,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            data_normalizer=data_normalizer,
            contract_policy=contract_policy,
        )
    )
    return transformer_class(
        provider=provider,
        entity_type=entity_type,
        silver_filters=silver_filters,
        gold_filters=gold_filters,
        dependencies=resolved_dependencies,
    )


def get_transformer_class(
    provider: str,
    entity_type: str,
) -> type[BaseTransformer] | None:
    """Get transformer class without instantiating.

    Args:
        provider: Provider name.
        entity_type: Entity type.

    Returns:
        Transformer class if registered, None otherwise.

    """
    return _TRANSFORMER_REGISTRY.get((provider, entity_type))


def _load_transformer_class(module_path: str, class_name: str) -> type:
    """Load transformer class by dotted module path and class name.

    Args:
        module_path: Dotted Python module path (e.g.,
            'bioetl.application.pipelines.chembl.activity_transformer').
        class_name: Name of the transformer class within the module.

    Returns:
        Transformer class type loaded from the module.

    Raises:
        TypeError: If the resolved attribute is not a class.
    """
    module = import_module(module_path)
    transformer_class = getattr(module, class_name)
    if not isinstance(transformer_class, type):
        raise TypeError(
            f"Expected class for {module_path}.{class_name}, "
            f"got {type(transformer_class).__name__}"
        )
    return transformer_class


def get_builtin_transformer_specs() -> tuple[TransformerRegistrationSpec, ...]:
    """Return declarative specs for built-in transformer registrations."""
    return _BUILTIN_TRANSFORMER_SPECS


def register_transformer_spec(
    spec: TransformerRegistrationSpec,
    *,
    load_transformer_class_fn: Callable[[str, str], type[BaseTransformer]]
    | None = None,
) -> None:
    """Register one transformer from a declarative module/class specification."""
    loader = (
        _load_transformer_class
        if load_transformer_class_fn is None
        else load_transformer_class_fn
    )
    register_transformer(
        spec.provider,
        spec.entity_type,
        loader(spec.module_path, spec.class_name),
    )


def register_all_transformers(
    specs: Iterable[TransformerRegistrationSpec] | None = None,
    *,
    load_transformer_class_fn: Callable[[str, str], type[BaseTransformer]]
    | None = None,
) -> None:
    """Register all known transformers.

    Called during application startup to populate the registry.
    Idempotent - safe to call multiple times.
    """
    spec_iter = get_builtin_transformer_specs() if specs is None else specs
    for spec in spec_iter:
        register_transformer_spec(
            spec,
            load_transformer_class_fn=load_transformer_class_fn,
        )


__all__ = [
    "TransformerRegistrationSpec",
    "create_transformer",
    "get_builtin_transformer_specs",
    "get_transformer_class",
    "register_all_transformers",
    "register_transformer",
    "register_transformer_spec",
]
