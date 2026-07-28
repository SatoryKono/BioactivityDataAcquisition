"""Schema-aware structural policy public facade helpers."""

from __future__ import annotations

from bioetl.application.core.base_transformer._structural_policy_support import (
    NoOpStructuralPolicy,
    SchemaAwareStructuralPolicy,
    build_structural_policy,
)
from bioetl.application.core.base_transformer._structural_policy_types import (
    StructuralFieldSpec,
    StructuralPolicyOutcome,
    StructuralPolicyProtocol,
    StructuralPolicySignal,
)

# Backward-compatible aliases retained for existing imports/tests.
StructuralFieldContract = StructuralFieldSpec
StructuralPolicyEvent = StructuralPolicySignal

__all__ = [
    "NoOpStructuralPolicy",
    "SchemaAwareStructuralPolicy",
    "StructuralFieldContract",
    "StructuralFieldSpec",
    "StructuralPolicyEvent",
    "StructuralPolicyOutcome",
    "StructuralPolicyProtocol",
    "StructuralPolicySignal",
    "build_structural_policy",
]
