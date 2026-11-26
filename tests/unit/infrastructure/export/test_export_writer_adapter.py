# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for ExportWriterAdapter."""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pytest

from bioetl.infrastructure.export import ExportWriterAdapter


pytestmark = pytest.mark.unit


@pytest.fixture
def table() -> pa.Table:
    return pa.Table.from_pydict({"col1": ["a", "b"], "col2": [1, 2]})


def test_write_export_creates_csv_file(
    table: pa.Table,
    tmp_path: Path,
) -> None:
    adapter = ExportWriterAdapter()

    output_path = Path(
        adapter.write_export(
            table=table,
            table_name="chembl.activity",
            layer="silver",
            fmt="csv",
            output_dir=str(tmp_path / "exports"),
        )
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
            output_dir=str(tmp_path / "exports"),
        )


def test_write_manifest_creates_stable_json(tmp_path: Path) -> None:
    adapter = ExportWriterAdapter()

    output_path = Path(
        adapter.write_manifest(
            manifest_name="silver_chembl_activity.provenance-manifest",
            payload={"b": 2, "a": 1},
            output_dir=str(tmp_path / "exports"),
        )
    )

    assert output_path.name == "silver_chembl_activity.provenance-manifest.json"
    import json

    assert json.loads(output_path.read_text(encoding="utf-8")) == {
        "a": 1,
        "b": 2,
        "spreadsheet_text_policy": "csv-tsv-apostrophe-prefix;xlsx-explicit-text;v1",
    }


def test_fingerprint_file_returns_sha256_and_size(tmp_path: Path) -> None:
    adapter = ExportWriterAdapter()
    output_path = tmp_path / "exports" / "data.csv"
    output_path.parent.mkdir()
    output_path.write_text("export", encoding="utf-8")

    fingerprint = adapter.fingerprint_file(path=str(output_path))

    assert fingerprint.path == str(output_path)
    assert fingerprint.size_bytes == 6
    assert fingerprint.sha256 == (
        "d46aee08cc49f6d1eb41800c1d6bab4506c960c700cff0efffe490d7cb1de5e3"
    )


def test_xlsx_round_trip_restores_long_text_classification_and_arrays(
    tmp_path: Path,
) -> None:
    import zipfile

    from openpyxl import load_workbook

    from bioetl.domain.config.target_classification import TARGET_CLASSIFICATION_FIELDS
    from bioetl.domain.serialization import serialize_to_json
    from bioetl.infrastructure.export.export_writer_adapter import (
        read_xlsx_export_manifest,
        restore_xlsx_table,
    )

    profile = "ab" * 32
    long_text = "Я" * (32767 * 2 + 11)
    exact = "e" * 32767
    subclasses = [{"b": 1, "a": "é"}, {"a": "z"}]
    families = [[("b", 1), ("a", 2)]]
    columns: dict[str, object] = {
        "target_id": ["CHEMBL1", "CHEMBL2"],
        "row_count_marker": [7, 8],
        "formula_text": ["=1+1", "+keep"],
        "exact_text": [exact, ""],
        "long_text": [long_text, None],
        "subclasses": [subclasses, None],
        "families": [*families, None],
        "_run_id": ["run-b", "run-a"],
    }
    for field in TARGET_CLASSIFICATION_FIELDS:
        columns[field] = [f"{field}-1", f"{field}-2"]
    columns["target_class_profile_sha256"] = [profile, profile]
    table = pa.table(
        {
            **{
                key: value
                for key, value in columns.items()
                if key not in {"subclasses", "families"}
            },
            "subclasses": pa.array(
                [subclasses, None],
                type=pa.list_(pa.struct([("b", pa.int64()), ("a", pa.string())])),
            ),
            "families": pa.array(
                [*families, None],
                type=pa.map_(pa.string(), pa.int64()),
            ),
        }
    )
    table = table.replace_schema_metadata({b"bioetl.table_version": b"12"})
    output = Path(
        ExportWriterAdapter().write_export(
            table=table,
            table_name="chembl.target",
            layer="silver",
            fmt="xlsx",
            output_dir=str(tmp_path / "exports"),
        )
    )

    assert zipfile.is_zipfile(output)
    with zipfile.ZipFile(output) as archive:
        content_types = archive.read("[Content_Types].xml")
    assert b"spreadsheetml.sheet.main+xml" in content_types
    workbook = load_workbook(output, data_only=False)
    try:
        sheet = workbook["Sheet1"]
        for row in sheet.iter_rows():
            for cell in row:
                if isinstance(cell.value, str):
                    assert len(cell.value) <= 32767
        formula_cells = [
            cell
            for row in sheet.iter_rows()
            for cell in row
            if cell.value in {"=1+1", "+keep"}
        ]
        assert formula_cells
        assert all(cell.data_type == "s" for cell in formula_cells)
    finally:
        workbook.close()

    manifest = read_xlsx_export_manifest(str(output))
    assert manifest["table_name"] == "chembl.target"
    assert manifest["layer"] == "silver"
    assert manifest["row_count"] == 2
    assert manifest["source_columns"] == list(table.column_names)
    identity = manifest["identity"]
    assert isinstance(identity, dict)
    assert identity["run_ids"] == ["run-a", "run-b"]
    assert identity["profile_sha256"] == [profile]
    assert identity["table_version"] == "12"
    part_columns = manifest["part_columns"]
    assert isinstance(part_columns, dict)
    assert "long_text" in part_columns
    assert "exact_text" not in part_columns

    restored = restore_xlsx_table(str(output))
    assert restored.column_names == list(table.column_names)
    assert restored.column("target_id").to_pylist() == ["CHEMBL1", "CHEMBL2"]
    assert restored.column("row_count_marker").to_pylist() == [7, 8]
    assert restored.column("formula_text").to_pylist() == ["=1+1", "+keep"]
    assert restored.column("exact_text").to_pylist() == [exact, ""]
    assert restored.column("long_text").to_pylist() == [long_text, None]
    assert restored.column("subclasses").to_pylist() == [
        serialize_to_json(table.column("subclasses").to_pylist()[0]),
        None,
    ]
    assert restored.column("families").to_pylist() == [
        serialize_to_json({"a": 2, "b": 1}),
        None,
    ]
    for field in TARGET_CLASSIFICATION_FIELDS:
        assert restored.column(field).to_pylist() == columns[field]


def test_xlsx_round_trip_keeps_null_rows_numbers_and_first_duplicate(
    tmp_path: Path,
) -> None:
    from bioetl.infrastructure.export.export_writer_adapter import restore_xlsx_table

    table = pa.Table.from_arrays(
        [
            pa.array(["CHEMBL1", None, "CHEMBL3", None]),
            pa.array([9606, None, None, None], type=pa.int64()),
            pa.array([5.0, None, 5.5, None], type=pa.float64()),
            pa.array([None, None, None, None], type=pa.string()),
            pa.array(["dropped", "also", "gone", "too"]),
        ],
        schema=pa.schema(
            [
                pa.field("target_id", pa.string()),
                pa.field("organism_id", pa.int64()),
                pa.field("score", pa.float64()),
                pa.field("blank", pa.string()),
                pa.field("target_id", pa.string()),
            ]
        ),
    )

    output = Path(
        ExportWriterAdapter().write_export(
            table=table,
            table_name="chembl.target",
            layer="gold",
            fmt="xlsx",
            output_dir=str(tmp_path / "exports"),
        )
    )
    restored = restore_xlsx_table(str(output))

    assert restored.num_rows == 4
    assert restored.column_names == ["target_id", "organism_id", "score", "blank"]
    assert restored.column("target_id").to_pylist() == [
        "CHEMBL1",
        None,
        "CHEMBL3",
        None,
    ]
    assert restored.column("organism_id").to_pylist() == [9606, None, None, None]
    assert restored.schema.field("organism_id").type == pa.int64()
    assert restored.schema.field("score").type == pa.float64()
    assert restored.column("score").to_pylist() == [5.0, None, 5.5, None]
    assert restored.column("blank").to_pylist() == [None, None, None, None]


def test_xlsx_round_trip_preserves_excel_unsafe_numbers(tmp_path: Path) -> None:
    import math

    from openpyxl import load_workbook

    from bioetl.infrastructure.export.export_writer_adapter import (
        read_xlsx_export_manifest,
        restore_xlsx_table,
    )

    large_id = 9_223_372_036_854_775_807
    precise = 1.2345678901234567
    subnormal = 5e-324
    table = pa.table(
        {
            "identifier": pa.array([large_id, -large_id, 37, None, 0], type=pa.int64()),
            "measurement": pa.array([precise, -0.0, subnormal, None, 1.25]),
        }
    )
    output = ExportWriterAdapter().write_export(
        table=table,
        table_name="chembl.assay_parameters",
        layer="silver",
        fmt="xlsx",
        output_dir=str(tmp_path),
    )

    workbook = load_workbook(output, read_only=True)
    try:
        assert list(workbook["Sheet1"].values)[1:] == [
            (str(large_id), repr(precise)),
            (str(-large_id), "-0.0"),
            (37, repr(subnormal)),
            (None, None),
            (0, 1.25),
        ]
    finally:
        workbook.close()
    assert read_xlsx_export_manifest(output)["numeric_text_columns"] == [
        "identifier",
        "measurement",
    ]
    restored = restore_xlsx_table(output)
    assert table.equals(restored)
    assert math.copysign(1.0, restored["measurement"][1].as_py()) == -1.0


def test_xlsx_text_part_name_collision_is_rejected(tmp_path: Path) -> None:
    table = pa.table(
        {
            "note": ["n" * 32768],
            "note__bioetl_part_0002": ["occupied"],
        }
    )

    with pytest.raises(ValueError, match="collides"):
        ExportWriterAdapter().write_export(
            table=table,
            table_name="chembl.target",
            layer="silver",
            fmt="xlsx",
            output_dir=str(tmp_path / "exports"),
        )


@pytest.mark.asyncio
async def test_catalog_export_round_trip_matches_delta_target(
    tmp_path: Path,
) -> None:
    """Silver and Gold target exports keep every Delta value.

    The fixed 1000/922 control extract is not in this repository. This test
    checks the same contract on a local Delta table: path, row identity,
    classification fields, long text, and run/profile/table version.
    """
    from deltalake import write_deltalake

    from bioetl.domain.config.target_classification import TARGET_CLASSIFICATION_FIELDS
    from bioetl.infrastructure.export.export_catalog_adapter import (
        ExportCatalogAdapter,
    )
    from bioetl.infrastructure.export.export_writer_adapter import (
        read_xlsx_export_manifest,
        restore_xlsx_table,
    )
    from bioetl.infrastructure.observability.noop_logger import NoOpLogger
    from bioetl.infrastructure.storage.delta_reader import DeltaReader

    profile = "cd" * 32
    long_text = "Δ" * 40000

    def build(run_id: str, identifiers: list[str]) -> pa.Table:
        count = len(identifiers)
        payload: dict[str, list[object]] = {
            "target_id": list(identifiers),
            "_run_id": [run_id] * count,
            "cross_references": [
                long_text if index == 0 else "short" for index in range(count)
            ],
        }
        for field in TARGET_CLASSIFICATION_FIELDS:
            payload[field] = [f"{field}:{run_id}"] * count
        payload["target_class_profile_sha256"] = [profile] * count
        return pa.table(payload)

    layers = {
        "silver": (
            tmp_path / "silver",
            ["CHEMBL1", "CHEMBL2", "CHEMBL3"],
            "run-silver",
        ),
        "gold": (tmp_path / "gold", ["CHEMBL9", "CHEMBL8"], "run-gold"),
    }
    catalog = ExportCatalogAdapter()
    writer = ExportWriterAdapter()
    for layer, (root, identifiers, run_id) in layers.items():
        table_dir = root / "chembl" / "target"
        write_deltalake(str(table_dir), build(run_id, identifiers))
        resolved = catalog.resolve_table_path(
            base_path=str(root),
            table_name="chembl.target",
            layer=layer,
        )
        assert resolved == str(table_dir.resolve())
        assert not (table_dir / "chembl.target").exists()
        loaded = await DeltaReader(root, NoOpLogger()).read_table(resolved)
        output = writer.write_export(
            table=loaded,
            table_name="chembl.target",
            layer=layer,
            fmt="xlsx",
            output_dir=str(tmp_path / "exports"),
        )
        restored = restore_xlsx_table(output)
        manifest = read_xlsx_export_manifest(output)
        identity = manifest["identity"]
        assert isinstance(identity, dict)
        assert identity["run_ids"] == [run_id]
        assert identity["profile_sha256"] == [profile]
        assert identity["table_version"] == loaded.schema.metadata[
            b"bioetl.table_version"
        ].decode("ascii")
        assert restored.num_rows == loaded.num_rows == len(identifiers)
        source_rows = {row["target_id"]: row for row in loaded.to_pylist()}
        restored_rows = {row["target_id"]: row for row in restored.to_pylist()}
        assert set(restored_rows) == set(identifiers)
        for target_id, source in source_rows.items():
            actual = restored_rows[target_id]
            assert actual["cross_references"] == source["cross_references"]
            for field in TARGET_CLASSIFICATION_FIELDS:
                assert actual[field] == source[field]
            assert actual["_run_id"] == run_id
