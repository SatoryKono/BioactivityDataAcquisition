"""Tests for SilverFilterConfig and relation with GoldFilterConfig."""

from __future__ import annotations

import pytest

from bioetl.domain.filtering.column_filter import GoldColumnFilter
from bioetl.domain.filtering.gold_config import GoldFilterConfig
from bioetl.domain.filtering.range_filter import GoldRangeFilter
from bioetl.domain.filtering.silver_config import SilverFilterConfig


@pytest.mark.unit
class TestFilterConfigTypeSeparation:
    """Gold and Silver configs are separate nominal types."""

    def test_gold_and_silver_are_not_subclasses_of_each_other(self) -> None:
        assert issubclass(GoldFilterConfig, SilverFilterConfig) is False
        assert issubclass(SilverFilterConfig, GoldFilterConfig) is False

    def test_instances_are_not_interchangeable_types(self) -> None:
        gold = GoldFilterConfig(required_fields=("id",))
        silver = SilverFilterConfig(required_fields=("id",))

        assert isinstance(gold, SilverFilterConfig) is False
        assert isinstance(silver, GoldFilterConfig) is False


@pytest.mark.unit
class TestSilverFromBaseAndBehavior:
    """from_base creates equivalent config behavior."""

    def test_from_base_copies_all_fields(self) -> None:
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


@pytest.mark.unit
class TestBaseFromBaseFactory:
    """BaseFilterConfig.from_base keeps logic in one place for all descendants."""

    def test_gold_from_base_copies_all_fields_and_type(self) -> None:
        source = GoldFilterConfig(
            required_fields=("id",),
            exclude_if_present=("deleted",),
            column_filters=(
                GoldColumnFilter(column="status", values=frozenset({"ACTIVE"})),
            ),
            range_filters=(
                GoldRangeFilter(column="score", min_value=0.0, max_value=10.0),
            ),
        )

        gold_copy = GoldFilterConfig.from_base(source)

        assert isinstance(gold_copy, GoldFilterConfig)
        assert gold_copy == source
