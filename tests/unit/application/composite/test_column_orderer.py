"""Tests for ColumnOrderer service."""

import polars as pl
import pytest
from unittest.mock import MagicMock

from bioetl.application.composite.column_orderer import ColumnOrderer
from bioetl.domain.value_objects.column_order import (
    ColumnOrderConfig,
    SemanticGroup,
)


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create mock logger."""
    logger = MagicMock()
    logger.debug = MagicMock()
    return logger


@pytest.fixture
def orderer(mock_logger: MagicMock) -> ColumnOrderer:
    """Create ColumnOrderer instance."""
    return ColumnOrderer(mock_logger)


class TestColumnOrderer:
    """Tests for ColumnOrderer."""

    def test_system_columns_first(self, orderer: ColumnOrderer) -> None:
        """System columns appear first."""
        df = pl.DataFrame(
            {
                "title": ["T1"],
                "_run_id": ["r1"],
                "doi": ["10.1/a"],
                "entity_id": ["e1"],
            }
        )
        result = orderer.order_columns(df)

        # System columns should be first
        assert result.columns[0] in ("entity_id", "_run_id")
        assert result.columns[1] in ("entity_id", "_run_id")

    def test_identifiers_before_content(self, orderer: ColumnOrderer) -> None:
        """Identifiers appear before content fields."""
        df = pl.DataFrame(
            {
                "abstract": ["A1"],
                "doi": ["10.1/a"],
                "title": ["T1"],
                "pmid": ["123"],
            }
        )
        result = orderer.order_columns(df)

        doi_idx = result.columns.index("doi")
        pmid_idx = result.columns.index("pmid")
        title_idx = result.columns.index("title")
        abstract_idx = result.columns.index("abstract")

        assert doi_idx < title_idx
        assert pmid_idx < title_idx
        assert title_idx < abstract_idx

    def test_title_before_abstract(self, orderer: ColumnOrderer) -> None:
        """Title fields appear before abstract fields."""
        df = pl.DataFrame(
            {
                "chembl.publication.abstract": ["A1"],
                "chembl.publication.title": ["T1"],
                "crossref.publication.title": ["T2"],
            }
        )
        result = orderer.order_columns(df)

        # All titles before abstracts
        title_indices = [
            i for i, c in enumerate(result.columns) if "title" in c.lower()
        ]
        abstract_indices = [
            i for i, c in enumerate(result.columns) if "abstract" in c.lower()
        ]

        assert max(title_indices) < min(abstract_indices)

    def test_provider_priority_within_group(self, orderer: ColumnOrderer) -> None:
        """Within same group, chembl comes before crossref."""
        df = pl.DataFrame(
            {
                "crossref.publication.title": ["T1"],
                "chembl.publication.title": ["T2"],
                "pubmed.publication.title": ["T3"],
            }
        )
        result = orderer.order_columns(df)

        chembl_idx = result.columns.index("chembl.publication.title")
        crossref_idx = result.columns.index("crossref.publication.title")
        pubmed_idx = result.columns.index("pubmed.publication.title")

        assert chembl_idx < crossref_idx < pubmed_idx

    def test_unqualified_columns_have_priority(self, orderer: ColumnOrderer) -> None:
        """Unqualified columns appear before qualified in same group."""
        df = pl.DataFrame(
            {
                "crossref.publication.title": ["T1"],
                "title": ["T2"],  # Unqualified = seed
            }
        )
        result = orderer.order_columns(df)

        title_idx = result.columns.index("title")
        crossref_idx = result.columns.index("crossref.publication.title")

        assert title_idx < crossref_idx

    def test_empty_dataframe(self, orderer: ColumnOrderer) -> None:
        """Empty DataFrame returns empty DataFrame."""
        df = pl.DataFrame()
        result = orderer.order_columns(df)
        assert len(result.columns) == 0

    def test_get_ordered_columns(self, orderer: ColumnOrderer) -> None:
        """Get ordered column names without DataFrame."""
        columns = ["abstract", "title", "_run_id", "doi"]
        ordered = orderer.get_ordered_columns(columns)

        assert ordered.index("_run_id") < ordered.index("doi")
        assert ordered.index("doi") < ordered.index("title")
        assert ordered.index("title") < ordered.index("abstract")

    def test_group_columns(self, orderer: ColumnOrderer) -> None:
        """Group columns by semantic type."""
        columns = [
            "_run_id",
            "doi",
            "chembl.publication.title",
            "crossref.publication.abstract",
        ]
        groups = orderer.group_columns(columns)

        assert "_run_id" in groups[SemanticGroup.SYSTEM]
        assert "doi" in groups[SemanticGroup.IDENTIFIERS]
        assert "chembl.publication.title" in groups[SemanticGroup.TITLE]
        assert "crossref.publication.abstract" in groups[SemanticGroup.ABSTRACT]

    def test_data_preserved_after_reorder(self, orderer: ColumnOrderer) -> None:
        """Data values are preserved after reordering."""
        df = pl.DataFrame(
            {
                "title": ["Title 1"],
                "_run_id": ["r1"],
                "doi": ["10.1/a"],
            }
        )
        result = orderer.order_columns(df)

        assert result["title"][0] == "Title 1"
        assert result["_run_id"][0] == "r1"
        assert result["doi"][0] == "10.1/a"

    def test_custom_config(self, mock_logger: MagicMock) -> None:
        """Custom configuration is respected."""
        config = ColumnOrderConfig(
            provider_priority=("crossref", "chembl")  # Reversed
        )
        orderer = ColumnOrderer(mock_logger, config)

        df = pl.DataFrame(
            {
                "chembl.publication.title": ["T1"],
                "crossref.publication.title": ["T2"],
            }
        )
        result = orderer.order_columns(df)

        # Crossref should come first with custom config
        crossref_idx = result.columns.index("crossref.publication.title")
        chembl_idx = result.columns.index("chembl.publication.title")

        assert crossref_idx < chembl_idx

    def test_full_publication_order(self, orderer: ColumnOrderer) -> None:
        """Full publication DataFrame is ordered correctly."""
        df = pl.DataFrame(
            {
                "citation_count": [100],
                "authors": [["Author 1"]],
                "journal": ["Nature"],
                "publication_date": ["2025-01-01"],
                "abstract": ["Abstract text"],
                "title": ["Title text"],
                "mesh_terms": [["term1"]],
                "doi": ["10.1/a"],
                "pmid": ["123"],
                "_run_id": ["r1"],
                "entity_id": ["e1"],
                "content_hash": ["hash1"],
                "pdf_url": ["http://example.com/pdf"],
            }
        )
        result = orderer.order_columns(df)

        # Verify semantic order
        # Within each group, columns are sorted alphabetically by field name
        # Note: underscore has lower ASCII value than letters, so _run_id comes first
        expected_order = [
            "_run_id",  # SYSTEM (underscore sorts before letters)
            "content_hash",  # SYSTEM
            "entity_id",  # SYSTEM
            "doi",  # IDENTIFIERS
            "pmid",  # IDENTIFIERS
            "title",  # TITLE
            "abstract",  # ABSTRACT
            "authors",  # AUTHORS
            "journal",  # JOURNAL
            "publication_date",  # DATES
            "citation_count",  # METRICS
            "mesh_terms",  # CLASSIFICATION
            "pdf_url",  # URLS
        ]

        assert result.columns == expected_order
