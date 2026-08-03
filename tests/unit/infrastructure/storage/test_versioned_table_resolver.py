# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
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
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for versioned physical table name resolution."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.storage.versioned_table_resolver import (
    resolve_read_candidates,
    resolve_versioned_table_name,
    resolve_write_targets,
)


@pytest.mark.unit
def test_resolve_versioned_table_name_appends_semver_suffix() -> None:
    """Resolver should keep logical name stable and append SemVer suffix."""
    assert (
        resolve_versioned_table_name("chembl.activity", "2.0.0")
        == "chembl.activity__v2_0_0"
    )


@pytest.mark.unit
def test_resolve_read_candidates_preserves_fallback_order() -> None:
    """Read candidates should preserve caller-provided fallback order."""
    assert resolve_read_candidates("chembl.activity", ["2.0.0", "1.0.0"]) == [
        "chembl.activity__v2_0_0",
        "chembl.activity__v1_0_0",
    ]


@pytest.mark.unit
def test_resolve_write_targets_preserves_write_order() -> None:
    """Write targets should preserve caller-provided write order."""
    assert resolve_write_targets("chembl.activity", ["1.0.0", "2.0.0"]) == [
        "chembl.activity__v1_0_0",
        "chembl.activity__v2_0_0",
    ]


@pytest.mark.unit
def test_resolve_versioned_table_name_rejects_invalid_semver() -> None:
    """Resolver should reject non-SemVer contract versions."""
    with pytest.raises(ValueError, match="SemVer"):
        resolve_versioned_table_name("chembl.activity", "2.0")
