"""Untrusted provider text stays inert at every spreadsheet export boundary."""

import csv
from pathlib import Path

import pyarrow as pa
import pytest

from bioetl.infrastructure.export.csv_exporter_table_ops import spreadsheet_safe_table
from bioetl.infrastructure.export.debug_export_ops import (
    write_debug_csv,
    write_debug_xlsx,
)
from bioetl.infrastructure.export.export_writer_adapter import ExportWriterAdapter

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "value", ["=1+1", "+1", "-1", "@SUM(1,1)", "\t=1", "\r=1", "\ufeff=1", "\u200b=1"]
)
@pytest.mark.parametrize("fmt", ["csv", "tsv", "xlsx"])
def test_formula_text_is_inert_and_source_numeric_values_unchanged(
    tmp_path, value, fmt
):
    table = pa.table({"=title": [value, None], "number": [-2, 3]})
    before = table.to_pydict()
    path = ExportWriterAdapter().write_export(
        table=table,
        table_name="audit",
        layer="silver",
        fmt=fmt,
        output_dir=str(tmp_path),
    )
    if fmt == "xlsx":
        from openpyxl import load_workbook

        with Path(path).open("rb") as handle:
            book = load_workbook(handle, data_only=False)
            assert book.active["A1"].data_type == "s"
            assert book.active["A2"].data_type == "s"
            assert book.active["A2"].value == value.replace("\r", "\n")
            assert book.active["B2"].value == -2
            assert book.active["B2"].data_type == "n"
            book.close()
    else:
        with Path(path).open(encoding="utf-8", newline="") as handle:
            rows = list(csv.reader(handle, delimiter="," if fmt == "csv" else "\t"))
        assert rows[0][0] == "'=title"
        assert rows[1] == ["'" + value, "-2"]
    assert table.to_pydict() == before


def test_safe_table_preserves_dictionary_text_and_is_idempotent():
    table = pa.table({"text": pa.array(["=1", "ordinary", None]).dictionary_encode()})
    safe = spreadsheet_safe_table(table)
    assert safe.column("text").to_pylist() == ["'=1", "ordinary", None]
    assert spreadsheet_safe_table(safe).equals(safe)
    assert table.column("text").to_pylist() == ["=1", "ordinary", None]


@pytest.mark.parametrize("fmt", ["csv", "tsv"])
def test_export_preserves_independent_dictionary_chunks(tmp_path, fmt):
    field = pa.field(
        "text", pa.dictionary(pa.int8(), pa.string()), metadata={b"origin": b"audit"}
    )
    chunks = [
        pa.DictionaryArray.from_arrays(
            pa.array([*range(100), None], type=pa.int8()),
            pa.array([f"=value-{chunk}-{value}" for value in range(100)]),
        )
        for chunk in range(2)
    ]
    table = pa.Table.from_arrays(
        [pa.chunked_array(chunks, type=field.type)], schema=pa.schema([field])
    )
    original = table.to_pydict()
    safe = spreadsheet_safe_table(table)
    assert safe.schema == table.schema
    assert safe.column("text").num_chunks == 2
    expected = [
        "'" + value if value is not None else None for value in original["text"]
    ]
    assert safe.column("text").to_pylist() == expected
    path = ExportWriterAdapter().write_export(
        table=table,
        table_name="dictionary",
        layer="silver",
        fmt=fmt,
        output_dir=str(tmp_path),
    )
    with Path(path).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle, delimiter="," if fmt == "csv" else "\t"))
    assert rows == [["text"], *[[] if value is None else [value] for value in expected]]
    assert table.to_pydict() == original


@pytest.mark.parametrize("include_bom", [False, True])
@pytest.mark.parametrize("existing", [False, True])
def test_debug_csv_rejects_colliding_headers_before_opening(
    tmp_path, include_bom, existing
):
    destination = tmp_path / "debug.csv"
    original = b"preserve existing audit evidence\n"
    if existing:
        destination.write_bytes(original)
    with pytest.raises(ValueError, match="Spreadsheet-safe column names collide"):
        write_debug_csv(
            destination,
            ({"=title": "first", "'=title": "second"},),
            include_bom=include_bom,
        )
    if existing:
        assert destination.read_bytes() == original
    else:
        assert not destination.exists()


def test_debug_csv_and_xlsx_do_not_create_formulas(tmp_path):
    from openpyxl import load_workbook

    rows = ({"=title": "=1+1", "number": -2},)
    csv_path = tmp_path / "debug.csv"
    write_debug_csv(csv_path, rows, include_bom=False)
    with csv_path.open(newline="") as handle:
        assert list(csv.reader(handle)) == [["'=title", "number"], ["'=1+1", "-2"]]
    xlsx = tmp_path / "debug.xlsx"
    write_debug_xlsx(
        xlsx,
        {"data": rows},
        max_rows_per_sheet=10,
    )
    book = load_workbook(xlsx, data_only=False)
    assert book.active["A1"].data_type == "s"
    assert book.active["A2"].data_type == "s"
    assert book.active["B2"].value == -2
    book.close()


def test_dev_environment_installs_xlsx_security_dependency():
    import tomllib
    import yaml

    root = Path(__file__).resolve().parents[4]
    workflow = yaml.safe_load((root / ".github/workflows/pr-required.yml").read_text())
    setup = next(
        step
        for step in workflow["jobs"]["class-lane"]["steps"]
        if step.get("id") == "setup-python"
    )
    assert "dev" in setup["with"]["uv-extras"].split()
    project = tomllib.loads((root / "pyproject.toml").read_text())
    assert any(
        item.startswith("openpyxl")
        for item in project["project"]["optional-dependencies"]["dev"]
    )


def test_failed_xlsx_write_preserves_error_and_keeps_partial_cells_inert(
    tmp_path, monkeypatch
):
    import pandas as pd
    from openpyxl import load_workbook

    def fail_after_write(self, writer, **kwargs):
        writer.book.active["A1"] = "=1+1"
        raise ValueError("synthetic write failure")

    monkeypatch.setattr(pd.DataFrame, "to_excel", fail_after_write)
    with pytest.raises(ValueError, match="synthetic write failure"):
        ExportWriterAdapter().write_export(
            table=pa.table({"title": ["=1+1"]}),
            table_name="audit",
            layer="silver",
            fmt="xlsx",
            output_dir=str(tmp_path),
        )
    book = load_workbook(tmp_path / "silver_audit.xlsx", data_only=False)
    assert book.active["A1"].data_type == "s"
    book.close()
