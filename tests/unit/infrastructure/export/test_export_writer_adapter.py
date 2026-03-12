"""Tests for ExportWriterAdapter."""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pytest

from bioetl.infrastructure.export import ExportWriterAdapter


@pytest.fixture
def table() -> pa.Table:
    return pa.Table.from_pydict({"col1": ["a", "b"], "col2": [1, 2]})


def test_write_export_creates_csv_file(
    table: pa.Table,
    tmp_path: Path,
) -> None:
    adapter = ExportWriterAdapter()

    output_path = adapter.write_export(
        table=table,
        table_name="chembl.activity",
        layer="silver",
        fmt="csv",
        output_dir=tmp_path / "exports",
    )

    assert output_path.exists()
    assert output_path.name == "silver_chembl_activity.csv"


def test_write_export_rejects_unsupported_format(
    table: pa.Table,
    tmp_path: Path,
) -> None:
    adapter = ExportWriterAdapter()

    with pytest.raises(ValueError, match="Unsupported format"):
        adapter.write_export(
            table=table,
            table_name="chembl.activity",
            layer="silver",
            fmt="json",
            output_dir=tmp_path / "exports",
        )
