"""Unit tests for CoalescePolicyService."""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.application.composite._coalesce_policy_support import (
    apply_field_priority,
    build_field_groups,
    build_latest_timestamp_row_fields,
    coalesce_by_latest_timestamp,
    count_timestamp_companions,
    drop_coalesced_columns,
    pick_latest_timestamp_value,
    resolve_priority_provider,
    resolve_row_timestamp_key,
    resolve_timestamp_companion,
    should_replace_latest_candidate,
    sort_columns,
    timestamp_sort_key,
    update_fallback_candidate,
)
from bioetl.application.composite.coalesce_policy import CoalescePolicyService


@pytest.fixture
def mock_logger() -> MagicMock:
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def mock_priority_orderer() -> MagicMock:
    orderer = MagicMock()
    orderer.collect_field_columns = MagicMock(return_value=[])
    orderer.order_columns_by_priority = MagicMock(return_value=[])
    orderer.filter_compatible_columns = MagicMock(return_value=([], []))
    return orderer


@pytest.fixture
def policy(
    mock_logger: MagicMock,
    mock_priority_orderer: MagicMock,
) -> CoalescePolicyService:
    return CoalescePolicyService(
        logger=mock_logger,
        priority_orderer=mock_priority_orderer,
    )


@pytest.mark.unit
def test_extract_field_from_qualified_and_plain_names() -> None:
    assert (
        CoalescePolicyService.extract_field_from_qualified("chembl.activity.title")
        == "title"
    )
    assert (
        CoalescePolicyService.extract_field_from_qualified("legacy_title")
        == "legacy_title"
    )


@pytest.mark.unit
def test_can_coalesce_handles_same_null_and_list_types() -> None:
    df = pl.DataFrame(
        {
            "int_a": [1],
            "int_b": [2],
            "null_col": [None],
            "list_a": [[1]],
            "list_b": [[2]],
            "scalar": [3],
        }
    )

    assert CoalescePolicyService.can_coalesce(df, "int_a", "int_b") is True
    assert CoalescePolicyService.can_coalesce(df, "int_a", "null_col") is True
    assert CoalescePolicyService.can_coalesce(df, "list_a", "list_b") is True
    assert CoalescePolicyService.can_coalesce(df, "list_a", "scalar") is False


@pytest.mark.unit
def test_coalesce_prefer_seed_coalesces_only_large_field_groups(
    policy: CoalescePolicyService,
) -> None:
    df = pl.DataFrame(
        {
            "chembl.publication.title": [None],
            "crossref.publication.title": ["crossref"],
            "openalex.publication.title": ["openalex"],
            "pubmed.publication.title": ["pubmed"],
            "semanticscholar.publication.title": ["ss"],
            "chembl.publication.year": [2020],
            "crossref.publication.year": [2021],
        }
    )

    result = policy.coalesce_prefer_seed(
        df, _enrichers=(), seed_pipeline="chembl_publication"
    )

    assert "chembl.publication.title" in result.columns
    assert "crossref.publication.title" not in result.columns
    assert result["chembl.publication.title"][0] == "crossref"
    assert "crossref.publication.year" in result.columns


@pytest.mark.unit
def test_coalesce_prefer_enricher_prioritizes_non_seed_column(
    policy: CoalescePolicyService,
) -> None:
    df = pl.DataFrame(
        {
            "chembl.publication.title": [None],
            "crossref.publication.title": ["crossref"],
        }
    )

    result = policy.coalesce_prefer_enricher(
        df,
        _enrichers=(),
        seed_pipeline="chembl_publication",
    )

    assert "crossref.publication.title" in result.columns
    assert "chembl.publication.title" not in result.columns
    assert result["crossref.publication.title"][0] == "crossref"


@pytest.mark.unit
def test_coalesce_prefer_latest_timestamp_prefers_newest_timestamped_source(
    policy: CoalescePolicyService,
) -> None:
    older = datetime(2026, 4, 1, tzinfo=UTC)
    newer = datetime(2026, 4, 2, tzinfo=UTC)
    df = pl.DataFrame(
        {
            "chembl.publication.title": ["seed-title"],
            "chembl.publication.updated_at": [older],
            "crossref.publication.title": ["crossref-title"],
            "crossref.publication.updated_at": [newer],
        }
    )

    result = policy.coalesce_prefer_latest_timestamp(
        df,
        _enrichers=(),
        seed_pipeline="chembl_publication",
    )

    assert "chembl.publication.title" in result.columns
    assert "crossref.publication.title" not in result.columns
    assert result["chembl.publication.title"][0] == "crossref-title"


@pytest.mark.unit
def test_coalesce_prefer_latest_timestamp_falls_back_to_seed_priority_without_companions(
    policy: CoalescePolicyService,
) -> None:
    df = pl.DataFrame(
        {
            "chembl.publication.title": ["seed-title"],
            "crossref.publication.title": ["crossref-title"],
        }
    )

    result = policy.coalesce_prefer_latest_timestamp(
        df,
        _enrichers=(),
        seed_pipeline="chembl_publication",
    )

    assert "chembl.publication.title" in result.columns
    assert "crossref.publication.title" not in result.columns
    assert result["chembl.publication.title"][0] == "seed-title"


@pytest.mark.unit
def test_apply_explicit_rules_coalesces_and_drops_extra_columns(
    policy: CoalescePolicyService,
    mock_priority_orderer: MagicMock,
) -> None:
    df = pl.DataFrame(
        {
            "seed.title": [None],
            "enricher.title": ["resolved"],
        }
    )
    mock_priority_orderer.collect_field_columns.return_value = [
        "seed.title",
        "enricher.title",
    ]
    mock_priority_orderer.order_columns_by_priority.return_value = [
        "seed.title",
        "enricher.title",
    ]
    mock_priority_orderer.filter_compatible_columns.return_value = (
        ["seed.title", "enricher.title"],
        [],
    )

    result = policy.apply_explicit_rules(
        df=df,
        enrichers=(),
        field_priorities={"title": ("seed", "enricher")},
        seed_pipeline="chembl_publication",
    )

    assert "seed.title" in result.columns
    assert "enricher.title" not in result.columns
    assert result["seed.title"][0] == "resolved"


@pytest.mark.unit
def test_apply_explicit_rules_skips_when_ordered_columns_are_empty(
    policy: CoalescePolicyService,
    mock_priority_orderer: MagicMock,
) -> None:
    df = pl.DataFrame({"seed.title": ["x"]})
    mock_priority_orderer.collect_field_columns.return_value = [
        "seed.title",
        "alt.title",
    ]
    mock_priority_orderer.order_columns_by_priority.return_value = []

    result = policy.apply_explicit_rules(
        df=df,
        enrichers=(),
        field_priorities={"title": ("seed",)},
        seed_pipeline="chembl_publication",
    )

    assert result.equals(df)


@pytest.mark.unit
def test_compatible_columns_and_coalesce_drop_helpers_cover_edge_cases() -> None:
    df = pl.DataFrame({"a": [1], "b": [2]})

    assert CoalescePolicyService._compatible_columns(df, []) == []

    unchanged = CoalescePolicyService._coalesce_and_drop(df, ["a"])
    assert unchanged.equals(df)


@pytest.mark.unit
def test_seed_prefix_returns_none_for_invalid_pipeline_name() -> None:
    assert CoalescePolicyService._seed_prefix("invalidname") is None


@pytest.mark.unit
def test_support_helpers_group_and_sort_branch_variants() -> None:
    df = pl.DataFrame(
        {
            "_system": [1],
            "chembl.publication.title": ["seed"],
            "crossref.publication.title": ["enricher"],
            "plain": ["plain"],
        }
    )

    assert build_field_groups(df) == {
        "title": ["chembl.publication.title", "crossref.publication.title"],
        "plain": ["plain"],
    }
    assert sort_columns(
        ["crossref.publication.title", "chembl.publication.title"],
        "chembl.publication.",
        prefer_seed=True,
    ) == ["chembl.publication.title", "crossref.publication.title"]
    assert sort_columns(
        ["crossref.publication.title", "chembl.publication.title"],
        "chembl.publication.",
        prefer_seed=False,
    ) == ["crossref.publication.title", "chembl.publication.title"]
    assert sort_columns(["b", "a"], None, prefer_seed=True) == ["a", "b"]


@pytest.mark.unit
def test_priority_provider_resolution_prefers_order_service_and_requires_fallback(
    mock_priority_orderer: MagicMock,
) -> None:
    order_service = MagicMock()

    assert (
        resolve_priority_provider(mock_priority_orderer, order_service) is order_service
    )
    assert (
        resolve_priority_provider(mock_priority_orderer, None) is mock_priority_orderer
    )
    with pytest.raises(AssertionError):
        resolve_priority_provider(None, None)


@pytest.mark.unit
def test_apply_field_priority_skips_when_rule_has_no_coalescing_work() -> None:
    df = pl.DataFrame({"seed.title": ["seed"]})
    provider = MagicMock()
    provider.collect_field_columns.return_value = ["seed.title"]

    result = apply_field_priority(
        df,
        provider=provider,
        field="title",
        priorities=("seed",),
        enrichers=(),
        available_columns=set(df.columns),
        seed_pipeline="chembl_publication",
        can_coalesce_fn=CoalescePolicyService.can_coalesce,
    )

    assert result.equals(df)
    provider.order_columns_by_priority.assert_not_called()
    provider.filter_compatible_columns.assert_not_called()


@pytest.mark.unit
def test_timestamp_companion_resolution_handles_missing_and_self_matches() -> None:
    available = {
        "chembl.publication.title",
        "chembl.publication.updated_at",
        "crossref.publication.title",
    }

    assert resolve_timestamp_companion("plain", available) is None
    assert (
        resolve_timestamp_companion("chembl.publication.title", available)
        == "chembl.publication.updated_at"
    )
    assert (
        resolve_timestamp_companion("chembl.publication.updated_at", available) is None
    )


@pytest.mark.unit
def test_timestamp_selection_helpers_cover_fallback_and_tie_breaks() -> None:
    assert timestamp_sort_key(datetime(2026, 1, 2, tzinfo=UTC))[0] == 3
    assert timestamp_sort_key(date(2026, 1, 2))[0] == 3
    assert timestamp_sort_key(3)[0] == 2
    assert timestamp_sort_key("2026-01-02") == (1, "2026-01-02")
    assert timestamp_sort_key(object()) == (0, "")

    assert update_fallback_candidate(
        value="new",
        rank=2,
        fallback_value="old",
        fallback_rank=1,
    ) == ("old", 1)
    assert (
        resolve_row_timestamp_key(
            row={"ts": datetime(2026, 1, 2, tzinfo=UTC)},
            column="value",
            timestamp_columns={"value": "ts"},
        )[0]
        == 3
    )
    assert (
        resolve_row_timestamp_key(
            row={"ts": None},
            column="value",
            timestamp_columns={"value": "ts"},
        )
        is None
    )

    best_key = timestamp_sort_key("2026-01-02")
    assert should_replace_latest_candidate(
        current_timestamp_key=timestamp_sort_key("2026-01-03"),
        rank=2,
        best_timestamp_key=best_key,
        best_rank=1,
    )
    assert should_replace_latest_candidate(
        current_timestamp_key=best_key,
        rank=0,
        best_timestamp_key=best_key,
        best_rank=1,
    )
    assert not should_replace_latest_candidate(
        current_timestamp_key=best_key,
        rank=0,
        best_timestamp_key=best_key,
        best_rank=None,
    )


@pytest.mark.unit
def test_latest_timestamp_row_helpers_pick_fallback_and_drop_redundant_columns() -> (
    None
):
    compatible_cols = ["seed.title", "alt.title"]
    timestamp_columns = {"seed.title": None, "alt.title": None}

    assert count_timestamp_companions(timestamp_columns) == 0
    assert build_latest_timestamp_row_fields(compatible_cols, timestamp_columns) == (
        compatible_cols
    )
    assert (
        pick_latest_timestamp_value(
            row={"seed.title": None, "alt.title": "alt"},
            compatible_cols=compatible_cols,
            timestamp_columns=timestamp_columns,
            priority_rank={"seed.title": 0, "alt.title": 1},
        )
        == "alt"
    )

    df = pl.DataFrame({"seed.title": [None], "alt.title": ["alt"], "keep": [1]})
    dropped = drop_coalesced_columns(df, compatible_cols)
    assert dropped.columns == ["seed.title", "keep"]


@pytest.mark.unit
def test_coalesce_by_latest_timestamp_returns_unchanged_for_single_column() -> None:
    df = pl.DataFrame({"seed.title": ["seed"]})

    assert coalesce_by_latest_timestamp(df, ordered_cols=["seed.title"]).equals(df)
