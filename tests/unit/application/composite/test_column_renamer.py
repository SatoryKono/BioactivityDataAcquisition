"""Tests for ColumnRenamer Service."""

import polars as pl
import pytest
from unittest.mock import MagicMock

from bioetl.application.composite.column_renamer import ColumnRenamer


@pytest.fixture
def mock_logger():
    return MagicMock()


@pytest.fixture
def renamer(mock_logger):
    return ColumnRenamer(mock_logger)


def test_rename_all_columns(renamer):
    """Test renaming of normal business columns."""
    df = pl.DataFrame({"title": ["A"], "year": [2020]})
    pipeline = "chembl_publication"

    result = renamer.rename_dataframe(df, pipeline)

    assert "chembl.publication.title" in result.columns
    assert "chembl.publication.year" in result.columns
    assert "title" not in result.columns


def test_exclude_join_keys(renamer):
    """Test that join keys are not renamed by default."""
    df = pl.DataFrame({"doi": ["10.1000/1"], "title": ["A"]})
    pipeline = "chembl_publication"

    result = renamer.rename_dataframe(df, pipeline, exclude_join_keys=True)

    assert "doi" in result.columns
    assert "chembl.publication.title" in result.columns


def test_include_join_keys(renamer):
    """Test that join keys ARE renamed if exclude_join_keys=False."""
    df = pl.DataFrame({"doi": ["10.1000/1"]})
    pipeline = "chembl_publication"

    result = renamer.rename_dataframe(df, pipeline, exclude_join_keys=False)

    assert "chembl.publication.doi" in result.columns
    assert "doi" not in result.columns


def test_skip_system_columns(renamer):
    """Test that system columns (starting with _) are skipped."""
    df = pl.DataFrame({"_ingestion_ts": ["2020"], "title": ["A"]})
    pipeline = "chembl_publication"

    result = renamer.rename_dataframe(df, pipeline)

    assert "_ingestion_ts" in result.columns
    assert "chembl.publication.title" in result.columns


def test_skip_already_qualified(renamer):
    """Test that already qualified columns are skipped."""
    # Assuming "chembl.publication.title" looks like a qualified name
    df = pl.DataFrame({"chembl.publication.title": ["A"], "other": ["B"]})
    pipeline = "chembl_publication"

    result = renamer.rename_dataframe(df, pipeline)

    assert "chembl.publication.title" in result.columns
    assert "chembl.publication.other" in result.columns


def test_invalid_pipeline_format(renamer, mock_logger):
    """Test handling of invalid pipeline name."""
    df = pl.DataFrame({"title": ["A"]})
    pipeline = "invalidpipeline"

    # Should log warning and skip renaming
    result = renamer.rename_dataframe(df, pipeline)

    assert "title" in result.columns
    mock_logger.warning.assert_called()


def test_case_insensitive_join_keys(renamer):
    """Test that join keys are detected case-insensitively."""
    df = pl.DataFrame({"DOI": ["1"], "pmID": ["2"]})
    pipeline = "chembl_publication"

    result = renamer.rename_dataframe(df, pipeline, exclude_join_keys=True)

    assert "DOI" in result.columns
    assert "pmID" in result.columns
