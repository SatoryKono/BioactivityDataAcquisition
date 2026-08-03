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
"""Tests for canonical column ordering contract."""

from __future__ import annotations

import pytest

from bioetl.domain.schemas.column_order import (
    ALL_SYSTEM_FIELDS,
    DQ_FIELDS_SUFFIX,
    SYSTEM_FIELDS_PREFIX,
    canonical_column_order,
)

pytestmark = pytest.mark.unit


def test_canonical_column_order_places_system_prefix_first() -> None:
    columns = ["_dq_warn", "z_field", "entity_id", "content_hash", "_run_id", "a_field"]
    ordered = canonical_column_order(columns)
    assert ordered[:3] == ["entity_id", "content_hash", "_run_id"]
    assert ordered[-1] == "_dq_warn"
    assert ordered[3:5] == ["a_field", "z_field"]


def test_canonical_column_order_preserves_lookup_fields() -> None:
    columns = ["entity_id", "_lookup_method", "_original_id", "activity_id"]
    ordered = canonical_column_order(columns)
    assert ordered == ["entity_id", "_lookup_method", "_original_id", "activity_id"]


def test_all_system_fields_matches_prefix_and_suffix() -> None:
    assert SYSTEM_FIELDS_PREFIX[0] == "entity_id"
    assert DQ_FIELDS_SUFFIX == ("_dq_error", "_dq_warn")
    for field in SYSTEM_FIELDS_PREFIX:
        assert field in ALL_SYSTEM_FIELDS
    for field in DQ_FIELDS_SUFFIX:
        assert field in ALL_SYSTEM_FIELDS
