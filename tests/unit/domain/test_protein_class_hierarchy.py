# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Unit tests for protein class hierarchy value objects."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from bioetl.domain.value_objects.protein_class_hierarchy import (
    ProteinClassHierarchy,
    ProteinClassLevel,
)


pytestmark = pytest.mark.unit


def test_protein_class_hierarchy_is_immutable_and_exposes_level_ids() -> None:
    hierarchy = ProteinClassHierarchy(
        l1=ProteinClassLevel(id=1, name="Ion channel", desc="Root"),
        l2=ProteinClassLevel(id=2, name="Voltage-gated", desc=None),
        l3=ProteinClassLevel.empty(),
        l4=ProteinClassLevel.empty(),
        l5=ProteinClassLevel.empty(),
        leaf_id=2,
    )

    assert hierarchy.level_ids == (1, 2, None, None, None)
    with pytest.raises(FrozenInstanceError):
        hierarchy.leaf_id = 3  # type: ignore[misc]


def test_protein_class_hierarchy_rejects_noncontiguous_levels() -> None:
    with pytest.raises(ValueError, match="contiguous"):
        ProteinClassHierarchy(
            l1=ProteinClassLevel(id=1, name="Root", desc=None),
            l2=ProteinClassLevel.empty(),
            l3=ProteinClassLevel(id=3, name="Broken", desc=None),
            l4=ProteinClassLevel.empty(),
            l5=ProteinClassLevel.empty(),
            leaf_id=3,
        )


def test_empty_protein_class_level_cannot_carry_text() -> None:
    with pytest.raises(ValueError, match="empty protein class levels"):
        ProteinClassLevel(id=None, name="HGNC-like text", desc=None)
