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
"""Tests for SilverFilterConfig and GoldFilterConfig nominal separation."""

from __future__ import annotations

import pytest

from bioetl.domain.filtering import BaseFilterConfig
from bioetl.domain.filtering.column_filter import GoldColumnFilter
from bioetl.domain.filtering.gold_config import GoldFilterConfig
from bioetl.domain.filtering.list_filters import (
    GoldListContainsFilter,
    GoldListLengthFilter,
)
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

    def test_from_base_keeps_legacy_semantic_buckets_but_runtime_is_structural_only(
        self,
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

        assert silver.column_filters == gold.column_filters
        assert silver.range_filters == gold.range_filters
        assert silver.should_include({"id": "1", "status": "INACTIVE", "score": 11})
        assert not silver.should_include(
            {"id": "1", "status": "ACTIVE", "score": 3.5, "deleted": True}
        )
        assert not silver.should_include({"status": "ACTIVE", "score": 3.5})


@pytest.mark.unit
class TestSilverStructuralOnlyRuntime:
    """Direct SilverFilterConfig construction cannot create semantic gates."""

    def test_column_and_range_filters_do_not_reject_silver_records(self) -> None:
        silver = SilverFilterConfig(
            column_filters=(
                GoldColumnFilter(column="status", values=frozenset({"ACTIVE"})),
            ),
            range_filters=(
                GoldRangeFilter(column="score", min_value=0.0, max_value=10.0),
            ),
        )

        decision = silver.evaluate({"status": "INACTIVE", "score": 99})

        assert decision.include is True
        assert silver.should_include({"status": "INACTIVE", "score": 99})
        assert silver.is_empty()

    def test_list_filters_do_not_reject_silver_records(self) -> None:
        silver = SilverFilterConfig(
            list_length_filters=(GoldListLengthFilter(column="tags", min_length=2),),
            list_contains_filters=(
                GoldListContainsFilter(
                    column="tags",
                    values=frozenset({"approved"}),
                    mode="all",
                ),
            ),
        )

        decision = silver.evaluate({"tags": ["rejected"]})

        assert decision.include is True
        assert silver.should_include({"tags": ["rejected"]})
        assert silver.is_empty()

    @pytest.mark.parametrize(
        ("silver", "record", "reason_code"),
        [
            (
                SilverFilterConfig(required_fields=("id",)),
                {"status": "ACTIVE"},
                "required_field_missing",
            ),
            (
                SilverFilterConfig(exclude_if_present=("deleted",)),
                {"id": "1", "deleted": True},
                "exclude_if_present",
            ),
        ],
    )
    def test_structural_filters_still_reject_silver_records(
        self,
        silver: SilverFilterConfig,
        record: dict[str, object],
        reason_code: str,
    ) -> None:
        decision = silver.evaluate(record)

        assert decision.include is False
        assert decision.reason_code == reason_code
        assert not silver.should_include(record)
        assert not silver.is_empty()
