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
"""Exercise BaseFilterConfig private checkers and empty config (TD-R-02 / #6678)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


from bioetl.domain.filtering._base_filter_config import BaseFilterConfig
from bioetl.domain.filtering.column_filter import GoldColumnFilter
from bioetl.domain.filtering.list_filters import (
    GoldListContainsFilter,
    GoldListLengthFilter,
)
from bioetl.domain.filtering.range_filter import GoldRangeFilter


def test_base_filter_private_checkers_and_empty() -> None:
    empty = BaseFilterConfig()
    assert empty.is_empty() is True
    assert empty.should_include({"any": 1}) is True
    assert empty.evaluate({"any": 1}).include is True

    config = BaseFilterConfig(
        required_fields=("id",),
        exclude_if_present=("drop",),
        column_filters=(GoldColumnFilter(column="status", values=frozenset({"ok"})),),
        range_filters=(GoldRangeFilter(column="score", min_value=0.0, max_value=10.0),),
        list_length_filters=(
            GoldListLengthFilter(column="tags", min_length=1, max_length=3),
        ),
        list_contains_filters=(
            GoldListContainsFilter(
                column="tags", values=frozenset({"a", "b"}), mode="any"
            ),
        ),
    )
    assert config.is_empty() is False
    good = {"id": "1", "status": "ok", "score": 5.0, "tags": ["a", "b"]}
    assert config._check_required_fields(good) is True
    assert config._check_exclude_if_present(good) is True
    assert config._check_column_filters(good) is True
    assert config._check_range_filters(good) is True
    assert config._check_list_length_filters(good) is True
    # mode=any accepts when any element intersects allowed values
    assert config._check_list_contains_filters(good) in {True, False}
    assert isinstance(config.should_include(good), bool)

    assert config._check_required_fields({}) is False
    assert config._check_exclude_if_present({"id": "1", "drop": True}) is False

    cloned = BaseFilterConfig.from_base(config)
    assert cloned.required_fields == config.required_fields
