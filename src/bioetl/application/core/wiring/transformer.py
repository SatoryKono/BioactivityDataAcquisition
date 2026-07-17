"""Stable application-core seam for composition-owned transformer wiring.

This compatibility facade preserves historical imports without eagerly loading
the transformer support graph during module initialization. Static exports are
declared in the adjacent stub.
"""

from __future__ import annotations

from bioetl.application.core.wiring._lazy_export_facade import (
    install_lazy_export_facade,
)

_PUBLIC_EXPORTS = {
    "BaseTransformer": "bioetl.application.core.base_transformer",
    "DefaultContractPolicy": (
        "bioetl.application.core.base_transformer.contract_policy"
    ),
    "NoOpStructuralPolicy": (
        "bioetl.application.core.base_transformer.structural_policy"
    ),
    "StructuralPolicyProtocol": (
        "bioetl.application.core.base_transformer.structural_policy"
    ),
    "TransformerDependencyContext": "bioetl.application.core.base_transformer",
    "build_structural_policy": (
        "bioetl.application.core.base_transformer.structural_policy"
    ),
}

install_lazy_export_facade(globals(), __name__, _PUBLIC_EXPORTS)

__all__: list[str]
