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
"""Unit tests for infrastructure export adapters."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import pyarrow as pa

import bioetl.infrastructure.export.debug_export_adapter as debug_adapter_module
from bioetl.domain.lineage import (
    LineageEdge,
    LineageEdgeType,
    LineageGraphFragment,
    LineageNodeRef,
    LineageNodeType,
)
from bioetl.domain.types import DebugExportPack
from bioetl.infrastructure.export.csv_exporter import CsvExporter
from bioetl.infrastructure.export.debug_export_adapter import DebugExportAdapter
from bioetl.infrastructure.export.export_catalog_adapter import ExportCatalogAdapter

pytestmark = pytest.mark.unit


class _Logger:
    def __init__(self) -> None:
        self.events: list[tuple[str, str, dict[str, Any]]] = []

    def warning(self, message: str, **kwargs: Any) -> None:
        self.events.append(("warning", message, kwargs))

    def info(self, message: str, **kwargs: Any) -> None:
        self.events.append(("info", message, kwargs))

    def debug(self, message: str, **kwargs: Any) -> None:
        self.events.append(("debug", message, kwargs))


def _pack(tmp_path: Path, **overrides: Any) -> DebugExportPack:
    defaults = {
        "run_id": "00000000-0000-0000-0000-000000000123",
        "pipeline_id": "chembl_activity",
        "provider_id": "chembl",
        "workflow_id": "wf-1",
        "manifest_id": "manifest-1",
        "status": "complete",
        "output_root": str(tmp_path),
        "formats": ("csv",),
        "include_bom": False,
        "max_rows_per_sheet": 1_000,
        "created_at": datetime(2026, 7, 5, 12, 0, tzinfo=UTC),
        "tables": {
            "rows": (
                {"b": 2, "a": {"nested": True}},
                {"a": ["x"], "c": None},
            )
        },
        "reason_dictionary": (),
    }
    defaults.update(overrides)
    return DebugExportPack(**defaults)


def test_debug_export_adapter_helper_methods_cover_csv_schema_hashes_and_paths(
    tmp_path: Path,
) -> None:
    adapter = DebugExportAdapter()
    rows = ({"b": 2, "a": {"nested": True}}, {"a": ["x"], "c": None})

    assert adapter._collect_headers(rows) == ["b", "a", "c"]
    assert adapter._collect_headers(()) == []
    assert adapter._normalize_csv_value(None) == ""
    assert adapter._normalize_csv_value({"b": 2, "a": 1}) == '{"a": 1, "b": 2}'
    assert adapter._normalize_csv_value(("x", "y")) == '["x", "y"]'
    assert adapter._normalize_csv_value("plain") == "plain"

    csv_path = tmp_path / "rows.csv"
    schema_path = tmp_path / "rows.schema.json"
    adapter._write_csv(csv_path, rows, include_bom=True)
    adapter._write_schema(schema_path, rows)

    csv_text = csv_path.read_text(encoding="utf-8-sig")
    assert '"b","a","c"' in csv_text
    assert '""nested"": true' in csv_text
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["columns"] == [
        {"name": "b", "types": ["int"]},
        {"name": "a", "types": ["dict", "list"]},
        {"name": "c", "types": []},
    ]

    fingerprint = adapter._fingerprint(csv_path, root_path=tmp_path)
    assert fingerprint["path"] == "rows.csv"
    assert fingerprint["size_bytes"] > 0
    assert isinstance(fingerprint["sha256"], str)
    assert "sha256" not in adapter._fingerprint(
        csv_path,
        include_content_hash=False,
    )
    assert adapter._compute_pack_hash([fingerprint]) == adapter._compute_pack_hash(
        [fingerprint]
    )

    relative_pack = _pack(Path("debug-output"), output_root="relative-output")
    assert adapter._resolve_root(relative_pack).is_absolute()
    absolute_pack = _pack(tmp_path)
    assert adapter._resolve_root(absolute_pack) == (
        tmp_path / "wf-1" / "chembl_activity" / absolute_pack.run_id
    )


def test_write_pack_persists_csv_schema_manifest_and_xlsx_skip_reason(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = DebugExportAdapter()

    def raise_missing_openpyxl(*_: Any, **__: Any) -> None:
        raise ModuleNotFoundError("No module named 'openpyxl'", name="openpyxl")

    monkeypatch.setattr(adapter, "_write_xlsx", raise_missing_openpyxl)
    result = adapter.write_pack(pack=_pack(tmp_path, formats=("csv", "xlsx")))

    root_path = Path(result.root_path)
    manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
    assert (root_path / "rows.csv").exists()
    assert (root_path / "rows.schema.json").exists()
    assert manifest["xlsx_skip_reason"].startswith("openpyxl is not installed")
    assert manifest["debug_export_hash"] == result.debug_export_hash
    assert [file["path"] for file in manifest["files"]] == [
        "rows.csv",
        "rows.schema.json",
    ]


def test_write_pack_csv_only_can_include_lineage_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = DebugExportAdapter()
    monkeypatch.setattr(
        adapter,
        "_load_lineage_rows",
        lambda pack: [{"fragment_id": "fragment-1", "node_id": "node-1"}],
    )

    result = adapter.write_pack(pack=_pack(tmp_path, formats=("csv",)))

    root_path = Path(result.root_path)
    assert (root_path / "rows.csv").exists()
    assert (root_path / "lineage.csv").exists()
    manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
    assert manifest["xlsx_skip_reason"] is None
    assert "debug_export.xlsx" not in {file["path"] for file in manifest["files"]}


def test_write_pack_records_successful_xlsx_artifact(tmp_path: Path) -> None:
    pytest.importorskip("openpyxl")

    adapter = DebugExportAdapter()
    result = adapter.write_pack(
        pack=_pack(
            tmp_path,
            formats=("csv", "xlsx"),
            max_rows_per_sheet=2,
            tables={
                "rows": (
                    {"value": 1},
                    {"value": 2},
                    {"value": 3},
                ),
                "empty": (),
            },
        )
    )

    root_path = Path(result.root_path)
    workbook_path = root_path / "debug_export.xlsx"
    assert workbook_path.exists()
    manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
    workbook_entries = [
        file for file in manifest["files"] if file["path"] == "debug_export.xlsx"
    ]
    assert workbook_entries == [
        {"path": "debug_export.xlsx", "size_bytes": workbook_path.stat().st_size}
    ]


def test_write_pack_re_raises_non_openpyxl_module_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = DebugExportAdapter()

    def raise_other_missing_module(*_: Any, **__: Any) -> None:
        raise ModuleNotFoundError("xlsxwriter")

    monkeypatch.setattr(adapter, "_write_xlsx", raise_other_missing_module)

    with pytest.raises(ModuleNotFoundError, match="xlsxwriter"):
        adapter.write_pack(pack=_pack(tmp_path, formats=("xlsx",)))


def test_load_lineage_rows_handles_no_store_errors_and_fragment_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert DebugExportAdapter()._load_lineage_rows(_pack(tmp_path)) == []

    class RaisingStore:
        def __init__(self, *, base_path: Path) -> None:
            del base_path
            raise OSError("unavailable")

    monkeypatch.setattr(debug_adapter_module, "FileLineageStore", RaisingStore)
    assert (
        DebugExportAdapter(lineage_store_path=str(tmp_path))._load_lineage_rows(
            _pack(tmp_path)
        )
        == []
    )

    source = LineageNodeRef(
        node_type=LineageNodeType.SOURCE_SYSTEM,
        node_id="node-1",
    )
    target = LineageNodeRef(
        node_type=LineageNodeType.DATASET,
        node_id="node-2",
    )
    fragment = LineageGraphFragment(
        fragment_id="fragment-1",
        stored_fragment_id="stored-1",
        manifest_id="manifest-1",
        run_id="00000000-0000-0000-0000-000000000123",
        nodes=(source,),
        edges=(
            LineageEdge(
                edge_type=LineageEdgeType.DERIVED_FROM,
                source=source,
                target=target,
            ),
        ),
    )

    class FakeStore:
        def __init__(self, *, base_path: Path) -> None:
            self.base_path = base_path

        def list_by_manifest_id(self, manifest_id: str) -> list[LineageGraphFragment]:
            assert manifest_id == "manifest-1"
            return [fragment]

        def list_by_run_id(self, run_id: object) -> list[LineageGraphFragment]:
            assert str(run_id) == "00000000-0000-0000-0000-000000000123"
            return [fragment]

    monkeypatch.setattr(debug_adapter_module, "FileLineageStore", FakeStore)
    adapter = DebugExportAdapter(lineage_store_path=str(tmp_path))
    rows = adapter._load_lineage_rows(_pack(tmp_path))
    assert rows == [
        {
            "fragment_id": "fragment-1",
            "stored_fragment_id": "stored-1",
            "manifest_id": "manifest-1",
            "run_id": "00000000-0000-0000-0000-000000000123",
            "node_id": "node-1",
            "edge_type": "",
            "related_node_id": "",
            "node_type": LineageNodeType.SOURCE_SYSTEM,
        },
        {
            "fragment_id": "fragment-1",
            "stored_fragment_id": "stored-1",
            "manifest_id": "manifest-1",
            "run_id": "00000000-0000-0000-0000-000000000123",
            "node_id": "node-1",
            "edge_type": LineageEdgeType.DERIVED_FROM,
            "related_node_id": "node-2",
            "node_type": "",
        },
    ]
    rows_by_run = adapter._load_lineage_rows(_pack(tmp_path, manifest_id=None))
    assert len(rows_by_run) == 2
    invalid_run_pack = _pack(tmp_path, manifest_id=None, run_id="not-a-uuid")
    assert adapter._load_lineage_rows(invalid_run_pack) == []


def test_csv_exporter_clear_and_deduplicate_branches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = _Logger()
    missing_exporter = CsvExporter(str(tmp_path / "missing"), logger=logger)
    assert missing_exporter.clear() == []

    base_path = tmp_path / "csv"
    base_path.mkdir()
    exporter = CsvExporter(str(base_path), logger=logger)
    table_a = base_path / "table_a.csv"
    locked = base_path / "locked.csv"
    free = base_path / "free.csv"
    table_a.write_text("id\n1\n", encoding="utf-8")
    locked.write_text("id\n2\n", encoding="utf-8")
    free.write_text("id\n3\n", encoding="utf-8")
    (base_path / "notes.txt").write_text("ignored", encoding="utf-8")

    assert exporter.clear("table_a") == [table_a]
    assert not table_a.exists()
    assert exporter.clear("missing") == []

    original_unlink = Path.unlink

    def maybe_raise_permission(
        self: Path,
        *args: object,
        **kwargs: object,
    ) -> None:
        if self == locked:
            raise PermissionError("locked")
        original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", maybe_raise_permission)

    assert exporter.clear() == [free]
    assert locked.exists()
    assert logger.events[-1] == (
        "warning",
        "Cannot delete locked CSV file",
        {"path": str(locked), "reason": "file may be open in another program"},
    )

    one_row = pa.table({"id": [1]})
    assert exporter._deduplicate_full_rows(one_row) is one_row
    unique_rows = pa.table({"id": [1, 2], "name": ["a", "b"]})
    assert exporter._deduplicate_full_rows(unique_rows) is unique_rows
    duplicate_rows = pa.table({"id": [1, 1, 2], "name": ["a", "a", "b"]})

    deduplicated = exporter._deduplicate_full_rows(duplicate_rows)

    assert deduplicated.to_pylist() == [
        {"id": 1, "name": "a"},
        {"id": 2, "name": "b"},
    ]
    assert logger.events[-1] == (
        "debug",
        "csv_export_table_deduplicated",
        {"removed_rows": 1},
    )


@pytest.mark.asyncio
async def test_csv_exporter_async_export_and_finalize_branches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = _Logger()
    exporter = CsvExporter(
        str(tmp_path),
        logger=logger,
        delimiter=";",
        header=False,
        sort_by=["id"],
        sort_ascending=False,
    )
    captured_writes: list[tuple[pa.Table, Path, object]] = []
    captured_appends: list[tuple[pa.Table, Path]] = []

    def capture_write(data: pa.Table, target_path: Path, write_options: object) -> None:
        captured_writes.append((data, target_path, write_options))
        target_path.write_text("id\n2\n", encoding="utf-8")

    def capture_append(data: pa.Table, csv_path: Path) -> None:
        captured_appends.append((data, csv_path))

    monkeypatch.setattr(exporter, "_atomic_csv_write", capture_write)
    monkeypatch.setattr(exporter, "_append_to_csv", capture_append)

    first_path = await exporter.export(
        "records",
        pa.table({"id": [1, 2]}),
        append=False,
        sort_by=["id"],
    )

    assert first_path == tmp_path / "records.csv"
    assert captured_writes[-1][1] == first_path
    assert captured_writes[-1][0].column("id").to_pylist() == [2, 1]

    second_path = await exporter.export(
        "records",
        pa.table({"id": [3]}),
        append=True,
    )

    assert second_path == first_path
    assert captured_appends[-1][1] == first_path
    assert captured_appends[-1][0].to_pylist() == [{"id": 3}]
    assert await exporter.finalize_csv("missing") is None

    deduplicated_tables: list[pa.Table] = []
    sorted_tables: list[pa.Table] = []

    def capture_deduplicate(table: pa.Table, primary_keys: list[str]) -> pa.Table:
        assert primary_keys == ["id"]
        deduplicated_tables.append(table)
        return table

    def capture_sort(table: pa.Table, sort_columns: list[str]) -> pa.Table:
        assert sort_columns == ["id"]
        sorted_tables.append(table)
        return table

    monkeypatch.setattr(exporter, "_deduplicate", capture_deduplicate)
    monkeypatch.setattr(exporter, "_sort_table", capture_sort)

    assert await exporter.finalize_csv("records", primary_keys=["id"]) == first_path
    assert deduplicated_tables
    assert sorted_tables
    assert logger.events[-1] == (
        "info",
        "csv_export_finalized",
        {
            "table_name": "records",
            "rows": 1,
            "deduplicated": True,
            "sorted": True,
        },
    )


def test_csv_exporter_export_table_uses_full_row_dedup_and_configured_sort(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = _Logger()
    exporter = CsvExporter(str(tmp_path), logger=logger, sort_by=["id"])
    captured_writes: list[tuple[pa.Table, Path, object]] = []

    def capture_write(data: pa.Table, target_path: Path, write_options: object) -> None:
        captured_writes.append((data, target_path, write_options))

    monkeypatch.setattr(exporter, "_atomic_csv_write", capture_write)
    output_path = tmp_path / "nested" / "records.csv"

    result = exporter.export_table(
        pa.table({"id": [2, 1, 2], "name": ["b", "a", "b"]}),
        str(output_path),
    )

    assert result == output_path
    assert output_path.parent.exists()
    assert captured_writes[-1][1] == output_path
    assert captured_writes[-1][0].to_pylist() == [
        {"id": 1, "name": "a"},
        {"id": 2, "name": "b"},
    ]


def test_export_catalog_adapter_lists_and_resolves_delta_tables(tmp_path: Path) -> None:
    adapter = ExportCatalogAdapter()
    base = tmp_path / "silver"

    assert adapter.list_tables(base_path=base, layer="silver") == []
    with pytest.raises(FileNotFoundError, match="Layer path not found"):
        adapter.resolve_table_path(
            base_path=base, table_name="activities", layer="silver"
        )

    table_dir = base / "chembl" / "activity" / "activities"
    (table_dir / "_delta_log").mkdir(parents=True)
    (base / "chembl" / "activity" / "not_delta").mkdir()
    (base / "chembl" / "activity" / "not_a_directory").write_text(
        "not a table",
        encoding="utf-8",
    )
    (base / "chembl" / "not_an_entity").write_text("not an entity", encoding="utf-8")
    (base / "README.txt").write_text("not a provider", encoding="utf-8")

    assert adapter.list_tables(base_path=base, layer="silver") == [
        ("activities", str(table_dir))
    ]
    assert adapter.resolve_table_path(
        base_path=base,
        table_name="activities",
        layer="silver",
    ) == str(table_dir.resolve())
    with pytest.raises(FileNotFoundError, match="Table 'missing' not found"):
        adapter.resolve_table_path(
            base_path=base,
            table_name="missing",
            layer="silver",
        )
