import polars as pl
import pytest

from bioetl.application.composite.column_renamer import ColumnRenamer


def test_rename_dataframe():
    renamer = ColumnRenamer()
    df = pl.DataFrame({"doi": ["10.1"], "title": ["A"], "_metadata": [1]})

    result = renamer.rename_dataframe(
        df, provider="chembl", entity="publication", exclude_columns={"doi"}
    )

    expected_cols = {"doi", "chembl.publication.title", "_metadata"}
    assert set(result.columns) == expected_cols
    assert result["doi"][0] == "10.1"
    assert result["chembl.publication.title"][0] == "A"


def test_rename_dataframe_idempotent():
    renamer = ColumnRenamer()
    df = pl.DataFrame({
        "chembl.publication.title": ["A"],
    })

    result = renamer.rename_dataframe(df, provider="chembl", entity="publication")

    assert result.columns == ["chembl.publication.title"]


def test_rename_dataframe_exclude_system():
    renamer = ColumnRenamer()
    df = pl.DataFrame({
        "title": ["A"],
        "_row_id": [1],
    })

    result = renamer.rename_dataframe(df, provider="chembl", entity="publication")

    assert "chembl.publication.title" in result.columns
    assert "_row_id" in result.columns
    assert "chembl.publication._row_id" not in result.columns
