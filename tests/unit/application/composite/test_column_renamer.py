"""Tests for ColumnRenamer service."""

import polars as pl
import pytest
from unittest.mock import MagicMock

from bioetl.application.composite.column_renamer import ColumnRenamer


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create mock logger."""
    logger = MagicMock()
    logger.debug = MagicMock()
    return logger


@pytest.fixture
def renamer(mock_logger: MagicMock) -> ColumnRenamer:
    """Create ColumnRenamer instance."""
    return ColumnRenamer(mock_logger)


class TestColumnRenamer:
    """Tests for ColumnRenamer."""

    def test_rename_all_business_columns(self, renamer: ColumnRenamer) -> None:
        """All business columns get qualified names."""
        df = pl.DataFrame(
            {
                "title": ["T1"],
                "abstract": ["A1"],
                "journal": ["J1"],
            }
        )
        result = renamer.rename_dataframe(df, "chembl_publication")

        assert "chembl.publication.title" in result.columns
        assert "chembl.publication.abstract" in result.columns
        assert "chembl.publication.journal" in result.columns

    def test_exclude_join_keys_by_default(self, renamer: ColumnRenamer) -> None:
        """Join keys are not renamed by default."""
        df = pl.DataFrame(
            {
                "doi": ["10.1/a"],
                "pmid": ["123"],
                "pmc_id": ["PMC456"],
                "title": ["T1"],
            }
        )
        result = renamer.rename_dataframe(df, "chembl_publication")

        assert "doi" in result.columns
        assert "pmid" in result.columns
        assert "pmc_id" in result.columns
        assert "chembl.publication.title" in result.columns

    def test_include_join_keys_when_disabled(self, renamer: ColumnRenamer) -> None:
        """Join keys are renamed when exclude_join_keys=False."""
        df = pl.DataFrame({"doi": ["10.1/a"], "title": ["T1"]})
        result = renamer.rename_dataframe(
            df, "chembl_publication", exclude_join_keys=False
        )

        assert "chembl.publication.doi" in result.columns
        assert "chembl.publication.title" in result.columns

    def test_skip_system_columns(self, renamer: ColumnRenamer) -> None:
        """System columns (starting with _) are not renamed."""
        df = pl.DataFrame(
            {
                "_run_id": ["r1"],
                "_ingestion_ts": ["2025-01-01"],
                "title": ["T1"],
            }
        )
        result = renamer.rename_dataframe(df, "chembl_publication")

        assert "_run_id" in result.columns
        assert "_ingestion_ts" in result.columns
        assert "chembl.publication.title" in result.columns

    def test_skip_already_qualified(self, renamer: ColumnRenamer) -> None:
        """Already qualified columns are not renamed."""
        df = pl.DataFrame(
            {
                "crossref.publication.title": ["T1"],
                "abstract": ["A1"],
            }
        )
        result = renamer.rename_dataframe(df, "chembl_publication")

        assert "crossref.publication.title" in result.columns
        assert "chembl.publication.abstract" in result.columns

    def test_empty_dataframe(self, renamer: ColumnRenamer) -> None:
        """Empty DataFrame returns empty DataFrame."""
        df = pl.DataFrame()
        result = renamer.rename_dataframe(df, "chembl_publication")
        assert len(result.columns) == 0

    def test_build_rename_map(self, renamer: ColumnRenamer) -> None:
        """Build correct rename mapping."""
        columns = ["title", "doi", "_run_id", "chembl.activity.name"]
        mapping = renamer.build_rename_map(columns, "chembl_publication")

        assert mapping == {"title": "chembl.publication.title"}

    def test_parse_pipeline_valid(self, renamer: ColumnRenamer) -> None:
        """Parse valid pipeline name."""
        provider, entity = renamer._parse_pipeline("chembl_publication")
        assert provider == "chembl"
        assert entity == "publication"

    def test_parse_pipeline_invalid(self, renamer: ColumnRenamer) -> None:
        """Reject pipeline without underscore."""
        with pytest.raises(ValueError, match="must be in format"):
            renamer._parse_pipeline("chemblpublication")

    def test_case_insensitive_join_keys(self, renamer: ColumnRenamer) -> None:
        """Join key detection is case-insensitive."""
        df = pl.DataFrame({"DOI": ["10.1/a"], "PMID": ["123"]})
        result = renamer.rename_dataframe(df, "chembl_publication")

        # Original case preserved but not renamed
        assert "DOI" in result.columns
        assert "PMID" in result.columns

    def test_data_preserved_after_rename(self, renamer: ColumnRenamer) -> None:
        """Data values are preserved after renaming."""
        df = pl.DataFrame(
            {
                "title": ["Title 1", "Title 2"],
                "doi": ["10.1/a", "10.1/b"],
            }
        )
        result = renamer.rename_dataframe(df, "chembl_publication")

        assert result["chembl.publication.title"].to_list() == ["Title 1", "Title 2"]
        assert result["doi"].to_list() == ["10.1/a", "10.1/b"]

    def test_normalization_to_lowercase(self, renamer: ColumnRenamer) -> None:
        """Provider and entity are normalized to lowercase."""
        df = pl.DataFrame({"title": ["T1"]})
        result = renamer.rename_dataframe(df, "ChEMBL_Publication")

        assert "chembl.publication.title" in result.columns
