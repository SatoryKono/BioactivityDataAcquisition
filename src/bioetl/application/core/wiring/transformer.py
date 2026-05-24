"""Stable application-core seam for composition-owned transformer wiring.

This compatibility facade preserves historical imports without eagerly loading
the transformer support graph during module initialization.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.core.base_transformer import (
        BaseTransformer,
        TransformerDependencyContext,
    )
    from bioetl.application.core.base_transformer.contract_policy import (
        DefaultContractPolicy,
    )
    from bioetl.application.core.base_transformer.structural_policy import (
        NoOpStructuralPolicy,
        StructuralPolicyProtocol,
        build_structural_policy,
    )

_PUBLIC_EXPORTS = {
    "BaseTransformer": (
        "bioetl.application.core.base_transformer",
        "BaseTransformer",
    ),
    "DefaultContractPolicy": (
        "bioetl.application.core.base_transformer.contract_policy",
        "DefaultContractPolicy",
    ),
    "NoOpStructuralPolicy": (
        "bioetl.application.core.base_transformer.structural_policy",
        "NoOpStructuralPolicy",
    ),
    "StructuralPolicyProtocol": (
        "bioetl.application.core.base_transformer.structural_policy",
        "StructuralPolicyProtocol",
    ),
    "TransformerDependencyContext": (
        "bioetl.application.core.base_transformer",
        "TransformerDependencyContext",
    ),
    "build_structural_policy": (
        "bioetl.application.core.base_transformer.structural_policy",
        "build_structural_policy",
    ),
}

__all__ = list(_PUBLIC_EXPORTS)


def __getattr__(name: str) -> object:
    export = _PUBLIC_EXPORTS.get(name)
    if export is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = export
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
