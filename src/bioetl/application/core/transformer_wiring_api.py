"""Stable application-core seam for composition-owned transformer wiring."""

from __future__ import annotations

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

__all__ = [
    "BaseTransformer",
    "DefaultContractPolicy",
    "NoOpStructuralPolicy",
    "StructuralPolicyProtocol",
    "TransformerDependencyContext",
    "build_structural_policy",
]
