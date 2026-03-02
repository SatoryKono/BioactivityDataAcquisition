"""Tests shared filter behavior inherited from BaseFilterConfig."""

from __future__ import annotations

import pytest

from bioetl.domain.filtering.column_filter import GoldColumnFilter
from bioetl.domain.filtering.gold_config import GoldFilterConfig
from bioetl.domain.filtering.range_filter import GoldRangeFilter
from bioetl.domain.filtering.silver_config import SilverFilterConfig


@pytest.mark.unit
@pytest.mark.parametrize("config_cls", [GoldFilterConfig, SilverFilterConfig])
def test_should_include_shared_logic(
    config_cls: type[GoldFilterConfig | SilverFilterConfig],
) -> None:
    """Gold and Silver must evaluate records identically with same config data."""
    config = config_cls(
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
