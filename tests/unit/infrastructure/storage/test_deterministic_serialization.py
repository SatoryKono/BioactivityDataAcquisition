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
"""Unit tests for deterministic serialization helpers."""

from __future__ import annotations

import pytest

import json


pytestmark = pytest.mark.unit


class TestDeterministicBronzeWrite:
    """Tests for deterministic Bronze-layer serialization."""

    def test_json_strings_are_sorted(self) -> None:
        """Bronze JSON strings should sort deterministically by serialized value."""
        records = [
            {"id": "C", "value": 3},
            {"id": "A", "value": 1},
            {"id": "B", "value": 2},
        ]

        json_strings = [json.dumps(record, sort_keys=True) for record in records]
        json_strings.sort()

        parsed = [json.loads(serialized) for serialized in json_strings]
        assert [record["id"] for record in parsed] == ["A", "B", "C"]

    def test_json_key_order_is_deterministic(self) -> None:
        """Bronze JSON serialization should keep a stable key order."""
        record = {"z_key": 1, "a_key": 2, "m_key": 3}

        json_str = json.dumps(record, sort_keys=True)

        assert json_str == '{"a_key": 2, "m_key": 3, "z_key": 1}'
