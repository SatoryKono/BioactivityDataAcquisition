"""Unit tests for canonical column-priority helper functions."""

from __future__ import annotations

from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.application.composite.column_service import ColumnOrderService
from bioetl.application.composite.column_priority_orderer import (
    get_enricher_prefix,
    resolve_priority_column,
)
from bioetl.application.composite.join_planner_helpers import parse_pipeline_name
from bioetl.domain.composite.config import EnricherConfig


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger."""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def orderer(mock_logger: MagicMock) -> ColumnOrderService:
    """Create service under test."""
    return ColumnOrderService(mock_logger)


def test_collect_field_columns_includes_seed_and_enricher_qualified_columns(
    orderer: ColumnOrderService,
) -> None:
    enrichers = (
        EnricherConfig(pipeline="crossref_publication", join_keys=("doi",)),
        EnricherConfig(pipeline="pubmed_publication", join_keys=("pmid",)),
    )
    available = {
        "chembl.publication.title",
        "crossref.publication.title",
        "pubmed.publication.abstract",
    }

    columns = orderer.collect_field_columns(
        field="title",
        enrichers=enrichers,
        available_columns=available,
        seed_pipeline="chembl_publication",
    )

    assert columns == ["chembl.publication.title", "crossref.publication.title"]


def test_collect_field_columns_falls_back_to_legacy_prefix_for_invalid_pipeline_names(
    orderer: ColumnOrderService,
    mock_logger: MagicMock,
) -> None:
    enrichers = (EnricherConfig(pipeline="legacycrossref", join_keys=("doi",)),)
    available = {"legacycrossref_title"}

    columns = orderer.collect_field_columns(
        field="title",
        enrichers=enrichers,
        available_columns=available,
        seed_pipeline="invalidseed",
    )

    assert columns == ["legacycrossref_title"]
    mock_logger.debug.assert_called_once()


def test_order_columns_by_priority_respects_seed_qualified_and_provider_order(
    orderer: ColumnOrderService,
) -> None:
    columns = [
        "pubchem.compound.title",
        "crossref.publication.title",
        "chembl.publication.title",
    ]
    ordered = orderer.order_columns_by_priority(
        field="title",
        columns=columns,
        priorities=("seed", "crossref.publication", "pubchem"),
        seed_pipeline="chembl_publication",
    )

    assert ordered == [
        "chembl.publication.title",
        "crossref.publication.title",
        "pubchem.compound.title",
    ]


def test_order_columns_by_priority_appends_remaining_columns_in_input_order(
    orderer: ColumnOrderService,
) -> None:
    columns = [
        "crossref.publication.title",
        "chembl.publication.title",
        "openalex.publication.title",
    ]
    ordered = orderer.order_columns_by_priority(
        field="title",
        columns=columns,
        priorities=("crossref.publication",),
        seed_pipeline=None,
    )

    assert ordered == [
        "crossref.publication.title",
        "chembl.publication.title",
        "openalex.publication.title",
    ]


def test_order_columns_by_priority_deduplicates_remaining_columns(
    orderer: ColumnOrderService,
) -> None:
    columns = [
        "crossref.publication.title",
        "openalex.publication.title",
        "openalex.publication.title",
    ]
    ordered = orderer.order_columns_by_priority(
        field="title",
        columns=columns,
        priorities=("crossref.publication",),
        seed_pipeline=None,
    )

    assert ordered == [
        "crossref.publication.title",
        "openalex.publication.title",
    ]


def test_filter_compatible_columns_returns_empty_for_no_ordered_columns(
    orderer: ColumnOrderService,
) -> None:
    df = pl.DataFrame({"a": [1]})
    compatible, incompatible = orderer.filter_compatible_columns(
        df=df,
        field="title",
        ordered_cols=[],
        can_coalesce=lambda _df, _base, _col: True,
    )
    assert compatible == []
    assert incompatible == []


def test_filter_compatible_columns_tracks_incompatible_columns_and_logs(
    orderer: ColumnOrderService,
    mock_logger: MagicMock,
) -> None:
    df = pl.DataFrame(
        {
            "seed.title": ["seed"],
            "crossref.title": ["crossref"],
            "pubmed.title": [1],
        }
    )
    compatible, incompatible = orderer.filter_compatible_columns(
        df=df,
        field="title",
        ordered_cols=["seed.title", "crossref.title", "pubmed.title"],
        can_coalesce=lambda _df, _base, col: col != "pubmed.title",
    )

    assert compatible == ["seed.title", "crossref.title"]
    assert incompatible == ["pubmed.title"]
    mock_logger.debug.assert_called_once()


def test_get_enricher_prefix_prefers_provider_entity_format() -> None:
    assert get_enricher_prefix("crossref_publication") == "crossref.publication."


def test_get_enricher_prefix_uses_legacy_format_when_pipeline_name_invalid() -> None:
    assert get_enricher_prefix("legacyname") == "legacyname_"


def test_parse_pipeline_name_raises_for_invalid_format() -> None:
    with pytest.raises(ValueError, match="must be in format"):
        parse_pipeline_name("invalid")


def test_resolve_priority_column_returns_none_for_seed_without_seed_context() -> None:
    resolved = resolve_priority_column(
        source="seed",
        field="title",
        columns_set={"crossref.publication.title"},
        seed_provider=None,
        seed_entity=None,
    )
    assert resolved is None
