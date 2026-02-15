"""Tests for SilverFilterConfig and GoldFilterConfig nominal separation."""

from __future__ import annotations

import pytest

from bioetl.domain.filtering import BaseFilterConfig
from bioetl.domain.filtering.column_filter import GoldColumnFilter
from bioetl.domain.filtering.gold_config import GoldFilterConfig
from bioetl.domain.filtering.range_filter import GoldRangeFilter
from bioetl.domain.filtering.silver_config import SilverFilterConfig


@pytest.mark.unit
class TestFilterConfigTypeSeparation:
    """Silver and Gold configs are nominally separated sibling types."""

    def test_silver_is_not_subclass_of_gold(self) -> None:
        assert issubclass(SilverFilterConfig, GoldFilterConfig) is False

    def test_gold_is_not_subclass_of_silver(self) -> None:
        assert issubclass(GoldFilterConfig, SilverFilterConfig) is False

    def test_both_inherit_base_filter_config(self) -> None:
        assert issubclass(SilverFilterConfig, BaseFilterConfig)
        assert issubclass(GoldFilterConfig, BaseFilterConfig)

    def test_silver_instance_is_not_gold_instance(self) -> None:
        silver = SilverFilterConfig(required_fields=("id",))
        assert isinstance(silver, GoldFilterConfig) is False

    def test_gold_instance_is_not_silver_instance(self) -> None:
        gold = GoldFilterConfig(required_fields=("id",))
        assert isinstance(gold, SilverFilterConfig) is False


@pytest.mark.unit
class TestSilverFromBase:
    """from_base creates equivalent config behavior."""

    def test_from_base_copies_all_fields(self) -> None:
        base = GoldFilterConfig(
            required_fields=("id",),
            exclude_if_present=("deleted",),
            column_filters=(
                GoldColumnFilter(column="status", values=frozenset({"ACTIVE"})),
            ),
            range_filters=(
                GoldRangeFilter(column="score", min_value=0.0, max_value=10.0),
            ),
        )

        silver = SilverFilterConfig.from_base(base)

        assert silver == SilverFilterConfig(
            required_fields=("id",),
            exclude_if_present=("deleted",),
            column_filters=(
                GoldColumnFilter(column="status", values=frozenset({"ACTIVE"})),
            ),
            range_filters=(
                GoldRangeFilter(column="score", min_value=0.0, max_value=10.0),
            ),
        )

    @pytest.mark.parametrize(
        "record",
        [
            {"id": "1", "status": "ACTIVE", "score": 3.5},
            {"id": "1", "status": "INACTIVE", "score": 3.5},
            {"id": "1", "status": "ACTIVE", "score": 11},
            {"id": "1", "status": "ACTIVE", "score": 3.5, "deleted": True},
            {"status": "ACTIVE", "score": 3.5},
        ],
    )
    def test_should_include_equivalent_for_same_content(
        self, record: dict[str, object]
    ) -> None:
        gold = GoldFilterConfig(
            required_fields=("id",),
            exclude_if_present=("deleted",),
            column_filters=(
                GoldColumnFilter(column="status", values=frozenset({"ACTIVE"})),
            ),
            range_filters=(
                GoldRangeFilter(column="score", min_value=0.0, max_value=10.0),
            ),
        )
        silver = SilverFilterConfig.from_base(gold)

        assert silver.should_include(record) == gold.should_include(record)
