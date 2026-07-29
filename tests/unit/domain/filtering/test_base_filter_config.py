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
"""Tests shared filter behavior inherited from BaseFilterConfig."""

from __future__ import annotations

import pytest

from bioetl.domain.filtering.column_filter import GoldColumnFilter
from bioetl.domain.filtering.gold_config import GoldFilterConfig
from bioetl.domain.filtering.range_filter import GoldRangeFilter


@pytest.mark.unit
def test_gold_should_include_uses_full_filter_logic() -> None:
    """Gold filter configs evaluate structural and semantic buckets."""
    config = GoldFilterConfig(
        required_fields=("id",),
        exclude_if_present=("deleted",),
        column_filters=(
            GoldColumnFilter(column="status", values=frozenset({"ACTIVE"})),
        ),
        range_filters=(GoldRangeFilter(column="score", min_value=0.0, max_value=10.0),),
    )

    assert config.should_include({"id": "1", "status": "ACTIVE", "score": 7.5})
    assert not config.should_include({"id": "1", "status": "INACTIVE", "score": 7.5})
    assert not config.should_include({"id": "1", "status": "ACTIVE", "score": 11})
    assert not config.should_include(
        {"id": "1", "status": "ACTIVE", "score": 7.5, "deleted": True}
    )
    assert not config.should_include({"status": "ACTIVE", "score": 7.5})
