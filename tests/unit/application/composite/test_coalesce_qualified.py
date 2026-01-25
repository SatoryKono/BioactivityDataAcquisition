"""Tests for coalesce with qualified column names."""

import polars as pl
import pytest
from unittest.mock import MagicMock

from bioetl.application.composite.merger import MergeService
from bioetl.domain.composite.config import MergeConfig
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create mock logger."""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    return logger


@pytest.fixture
def merge_config() -> MergeConfig:
    """Create minimal merge config."""
    return MergeConfig(
        strategy=MergeStrategy.LEFT_OUTER,
        conflict_resolution=ConflictResolution.SEED_PRIORITY,
        output_silver_path="silver/test",
        output_gold_path="gold/test",
    )


@pytest.fixture
def merge_service(merge_config: MergeConfig, mock_logger: MagicMock) -> MergeService:
    """Create MergeService instance."""
    storage = MagicMock()
    return MergeService(merge_config, storage, mock_logger)


class TestExtractFieldFromQualified:
    """Tests for _extract_field_from_qualified helper."""

    def test_three_parts_returns_field(self, merge_service: MergeService) -> None:
        """Extract field from three-part qualified name."""
        assert (
            merge_service._extract_field_from_qualified("chembl.publication.title")
            == "title"
        )

    def test_one_part_returns_original(self, merge_service: MergeService) -> None:
        """Return original for non-qualified name."""
        assert merge_service._extract_field_from_qualified("title") == "title"

    def test_two_parts_returns_original(self, merge_service: MergeService) -> None:
        """Return original for two-part name (not valid qualified)."""
        assert (
            merge_service._extract_field_from_qualified("crossref.title")
            == "crossref.title"
        )


class TestCoalescePreferSeed:
    """Tests for _coalesce_prefer_seed with qualified names."""

    def test_seed_wins_over_enricher(self, merge_service: MergeService) -> None:
        """Seed columns take priority in coalesce."""
        df = pl.DataFrame(
            {
                "doi": ["10.1/a"],
                "chembl.publication.title": ["Seed Title"],
                "crossref.publication.title": ["Enricher Title"],
                "_run_id": ["r1"],
            }
        )
        result = merge_service._coalesce_prefer_seed(
            df, enrichers=[], seed_pipeline="chembl_publication"
        )

        assert "chembl.publication.title" in result.columns
        assert result["chembl.publication.title"][0] == "Seed Title"
        assert "crossref.publication.title" not in result.columns

    def test_fills_null_from_enricher(self, merge_service: MergeService) -> None:
        """Coalesce fills nulls from lower priority columns."""
        df = pl.DataFrame(
            {
                "doi": ["10.1/a", "10.1/b"],
                "chembl.publication.title": [None, "Seed Title 2"],
                "crossref.publication.title": ["Enricher Title 1", "Enricher Title 2"],
            }
        )
        result = merge_service._coalesce_prefer_seed(
            df, enrichers=[], seed_pipeline="chembl_publication"
        )

        titles = result["chembl.publication.title"].to_list()
        assert titles[0] == "Enricher Title 1"  # Filled from enricher
        assert titles[1] == "Seed Title 2"  # Kept from seed


class TestCoalescePreferEnricher:
    """Tests for _coalesce_prefer_enricher with qualified names."""

    def test_enricher_wins_over_seed(self, merge_service: MergeService) -> None:
        """Enricher columns take priority in coalesce."""
        df = pl.DataFrame(
            {
                "doi": ["10.1/a"],
                "chembl.publication.title": ["Seed Title"],
                "crossref.publication.title": ["Enricher Title"],
            }
        )
        result = merge_service._coalesce_prefer_enricher(
            df, enrichers=[], seed_pipeline="chembl_publication"
        )

        assert "crossref.publication.title" in result.columns
        assert result["crossref.publication.title"][0] == "Enricher Title"
        assert "chembl.publication.title" not in result.columns
