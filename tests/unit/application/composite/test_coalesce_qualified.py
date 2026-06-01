"""Tests for coalesce with qualified column names."""

import polars as pl
import pytest
from unittest.mock import MagicMock

from bioetl.application.composite.merger import MergeService
from bioetl.domain.composite.config import MergeConfig
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy
from tests.unit.application.composite.merge_test_support import build_merge_service


pytestmark = pytest.mark.unit

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
    return build_merge_service(
        merge_config=merge_config,
        logger=mock_logger,
        storage=MagicMock(),
    )


class TestExtractFieldFromQualified:
    """Tests for _extract_field_from_qualified helper."""

    def test_three_parts_returns_field(self, merge_service: MergeService) -> None:
        """Extract field from three-part qualified name."""
        assert (
            merge_service._coalesce_policy.extract_field_from_qualified(
                "chembl.publication.title"
            )
            == "title"
        )

    def test_one_part_returns_original(self, merge_service: MergeService) -> None:
        """Return original for non-qualified name."""
        assert (
            merge_service._coalesce_policy.extract_field_from_qualified("title")
            == "title"
        )

    def test_two_parts_returns_original(self, merge_service: MergeService) -> None:
        """Return original for two-part name (not valid qualified)."""
        assert (
            merge_service._coalesce_policy.extract_field_from_qualified(
                "crossref.title"
            )
            == "crossref.title"
        )


class TestCoalescePreferSeed:
    """Tests for _coalesce_prefer_seed with qualified names.

    Note: Coalescing only occurs when a field has more than 4 columns
    (threshold set in commit 99e2391 to reduce processing for smaller groups).
    """

    def test_seed_wins_over_enricher(self, merge_service: MergeService) -> None:
        """Seed columns take priority when >4 columns exist for a field.

        With only 2 columns, coalesce is skipped (threshold is >4).
        """
        df = pl.DataFrame(
            {
                "doi": ["10.1/a"],
                "chembl.publication.title": ["Seed Title"],
                "crossref.publication.title": ["Enricher Title"],
                "openalex.publication.title": ["OA Title"],
                "pubmed.publication.title": ["PM Title"],
                "semanticscholar.publication.title": ["SS Title"],
                "_run_id": ["r1"],
            }
        )
        result = merge_service._coalesce_policy.coalesce_prefer_seed(
            df, _enrichers=[], seed_pipeline="chembl_publication"
        )

        assert "chembl.publication.title" in result.columns
        assert result["chembl.publication.title"][0] == "Seed Title"
        # Enricher columns should be dropped after coalesce
        assert "crossref.publication.title" not in result.columns

    def test_fills_null_from_enricher(self, merge_service: MergeService) -> None:
        """Coalesce fills nulls from lower priority columns when >4 exist."""
        df = pl.DataFrame(
            {
                "doi": ["10.1/a", "10.1/b"],
                "chembl.publication.title": [None, "Seed Title 2"],
                "crossref.publication.title": ["Enricher Title 1", "Enricher Title 2"],
                "openalex.publication.title": ["OA 1", "OA 2"],
                "pubmed.publication.title": ["PM 1", "PM 2"],
                "semanticscholar.publication.title": ["SS 1", "SS 2"],
            }
        )
        result = merge_service._coalesce_policy.coalesce_prefer_seed(
            df, _enrichers=[], seed_pipeline="chembl_publication"
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
        result = merge_service._coalesce_policy.coalesce_prefer_enricher(
            df, _enrichers=[], seed_pipeline="chembl_publication"
        )

        assert "crossref.publication.title" in result.columns
        assert result["crossref.publication.title"][0] == "Enricher Title"
        assert "chembl.publication.title" not in result.columns
