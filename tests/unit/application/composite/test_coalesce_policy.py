"""Unit tests for CoalescePolicyService."""

from __future__ import annotations

from unittest.mock import MagicMock

import polars as pl
import pytest

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
