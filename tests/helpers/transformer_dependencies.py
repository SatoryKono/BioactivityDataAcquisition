"""Test helper for explicit transformer collaborator wiring."""

from __future__ import annotations

import dataclasses
import inspect
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.application.core.base_transformer.structural_policy import (
        StructuralPolicyProtocol,
    )
    from bioetl.application.core.base_transformer.types import (
        TransformerDependencyContext,
    )
    from bioetl.domain.ports import (
        ContractPolicyProtocol,
        DataNormalizationPort,
        MetricsPort,
        PiiHasherPort,
        TracingPort,
    )
    from bioetl.domain.behavior import EntityIdentityGenerator

__all__ = [
    "build_test_transformer_dependencies",
    "instantiate_test_transformer",
]


def build_test_transformer_dependencies(
    *,
    tracer: TracingPort | None = None,
    metrics: MetricsPort | None = None,
    identity_service: EntityIdentityGenerator | None = None,
    pii_hasher: PiiHasherPort | None = None,
    data_normalizer: DataNormalizationPort | None = None,
    contract_policy: ContractPolicyProtocol | None = None,
    structural_policy: StructuralPolicyProtocol | None = None,
) -> TransformerDependencyContext:
    """Build transformer defaults without importing composition at collect time."""
    from bioetl.composition.factories.transformer_dependencies import (
        build_transformer_dependencies,
    )

    return build_transformer_dependencies(
        tracer=tracer,
        metrics=metrics,
        identity_service=identity_service,
        pii_hasher=pii_hasher,
        data_normalizer=data_normalizer,
        contract_policy=contract_policy,
        structural_policy=structural_policy,
    )


def instantiate_test_transformer[TTransformer](
    transformer_class: type[TTransformer],
    /,
    **kwargs: Any,
) -> TTransformer:
    """Instantiate a transformer using composition-owned default collaborators."""
    dependencies = build_test_transformer_dependencies()

    # Preserve constructor defaults for required context fields like `provider`
    # when tests intentionally omit them.
    init_signature = inspect.signature(transformer_class)
    provider_parameter = init_signature.parameters.get("provider")
    if (
        "provider" not in kwargs
        and provider_parameter is not None
        and provider_parameter.default is not inspect.Signature.empty
    ):
        kwargs["provider"] = provider_parameter.default

    # Route context-specific kwargs to the dependency bundle
    context_keys = {
        "tracer",
        "metrics",
        "identity_service",
        "pii_hasher",
        "data_normalizer",
        "contract_policy",
        "structural_policy",
    }
    context_kwargs = {k: v for k, v in kwargs.items() if k in context_keys}
    for k in context_kwargs:
        kwargs.pop(k)

    if context_kwargs:
        dependencies = dataclasses.replace(dependencies, **context_kwargs)

    return transformer_class(
        dependencies=dependencies,
        **kwargs,
    )
