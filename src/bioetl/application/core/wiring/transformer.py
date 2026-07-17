"""Stable application-core seam for composition-owned transformer wiring.

This compatibility facade preserves historical imports without eagerly loading
the transformer support graph during module initialization.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.wiring._lazy_export_facade import (
    install_lazy_export_facade,
)

if TYPE_CHECKING:
    from bioetl.application.core.base_transformer import (
        BaseTransformer as BaseTransformer,
    )
    from bioetl.application.core.base_transformer import (
        TransformerDependencyContext as TransformerDependencyContext,
    )
    from bioetl.application.core.base_transformer.contract_policy import (
        DefaultContractPolicy as DefaultContractPolicy,
    )
    from bioetl.application.core.base_transformer.structural_policy import (
        NoOpStructuralPolicy as NoOpStructuralPolicy,
    )
    from bioetl.application.core.base_transformer.structural_policy import (
        StructuralPolicyProtocol as StructuralPolicyProtocol,
    )
    from bioetl.application.core.base_transformer.structural_policy import (
        build_structural_policy as build_structural_policy,
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

install_lazy_export_facade(globals(), __name__, _PUBLIC_EXPORTS)

__all__: list[str]
