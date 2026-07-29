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
"""Unit tests for batch transformer attempt helpers."""

from __future__ import annotations

import pytest

from bioetl.application.core.batch_transformer_attempts import (
    _resolve_gold_filter_details,
)
from bioetl.domain.filtering import FilterOperator, GoldColumnFilter, GoldFilterConfig


class _GoldFilterOwner:
    def __init__(self, filters: GoldFilterConfig) -> None:
        self._gold_filters = filters

    def should_write_gold(self, _context, record: dict[str, object]) -> bool:
        return self._gold_filters.should_include(record)


@pytest.mark.unit
def test_resolve_gold_filter_details_returns_structured_decision() -> None:
    filters = GoldFilterConfig(
        column_filters=(
            GoldColumnFilter(
                column="bao_format",
                operator=FilterOperator.NOT_IN,
                values=frozenset({"BAO_0000218"}),
            ),
        )
    )
    owner = _GoldFilterOwner(filters)

    details = _resolve_gold_filter_details(
        owner.should_write_gold,
        {"bao_format": "BAO_0000218"},
    )

    assert details is not None
    assert details["field"] == "bao_format"
    assert details["operator"] == "not_in"
    assert details["actual"] == "BAO_0000218"
    assert details["expected"] == ["BAO_0000218"]
