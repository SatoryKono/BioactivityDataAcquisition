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
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict.
"""Unit tests for retention dedup primary-key helpers."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.storage.support.retention_dedup import (
    primary_key_sort_key,
    primary_key_tuple,
)

pytestmark = pytest.mark.unit


def test_primary_key_sort_key_total_orders_none() -> None:
    """Mixed None/str PK components must sort without TypeError."""
    rows = [
        {"id": None, "v": 1},
        {"id": "b", "v": 2},
        {"id": "a", "v": 3},
        {"id": None, "v": 4},
    ]
    keys = [primary_key_tuple(row, ("id",)) for row in rows]
    ranked = sorted(keys, key=primary_key_sort_key)
    assert ranked[0] == (None,)
    assert ranked[1] == (None,)
    assert {ranked[2], ranked[3]} == {("a",), ("b",)}
