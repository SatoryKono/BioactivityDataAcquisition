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
"""Unit tests for CsvExporter."""

from __future__ import annotations

import builtins
import csv
import hashlib
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pyarrow as pa
import pyarrow.csv as pv
import pytest

import bioetl.infrastructure.export.csv_exporter_table_ops as csv_exporter_table_ops
import bioetl.infrastructure.export.csv_exporter_io_ops as csv_exporter_io_ops
from bioetl.infrastructure.export.csv_exporter import (
    CsvExporter,
    _seed_raw_sidecar_if_missing,
)


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger for tests."""
    return MagicMock()


@pytest.mark.unit
class TestCsvExporterInit:
    """Tests for CsvExporter initialization."""

    def test_csv_exporter_init__init_with_defaults__8b2f7c42(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> None:
        """Test initialization with default parameters."""
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)

        assert exporter.base_path == tmp_path
        assert exporter.delimiter == ","
        assert exporter.header is True
        assert exporter.encoding == "utf-8"

    def test_init_with_custom_options(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> None:
        """Test initialization with custom parameters."""
        exporter = CsvExporter(
            base_path=str(tmp_path),
            logger=mock_logger,
            delimiter=";",
            header=False,
            encoding="latin-1",
        )

        assert exporter.delimiter == ";"
        assert exporter.header is False
        assert exporter.encoding == "latin-1"


@pytest.mark.unit
class TestCsvExporterFlatten:
    """Tests for _flatten_for_csv method."""

    def test_flatten_simple_types_returns_same_table(self) -> None:
        """Simple tables should bypass expensive flattening work."""
        table = pa.Table.from_pydict(
            {
                "id": [1, 2],
                "name": ["a", "b"],
                "value": [1.5, 2.5],
            }
        )

        result = CsvExporter._flatten_for_csv(table)

        assert result is table

    def test_flatten_simple_types(self) -> None:
        """Test that simple types are preserved."""
        table = pa.Table.from_pydict(
            {
                "id": [1, 2],
                "name": ["a", "b"],
                "value": [1.5, 2.5],
            }
        )

        result = CsvExporter._flatten_for_csv(table)

        assert result.schema == table.schema
        assert result.to_pydict() == table.to_pydict()

    def test_flatten_list_type(self) -> None:
        """Test that list types are converted to JSON strings."""
        table = pa.Table.from_pydict(
            {
                "id": [1, 2],
                "tags": [["a", "b"], ["c"]],
            }
        )

        result = CsvExporter._flatten_for_csv(table)

        assert pa.types.is_string(result.schema.field("tags").type)
        # Compact JSON format (no spaces) per centralized serialization
        assert result.column("tags").to_pylist() == ['["a","b"]', '["c"]']

    def test_flatten_struct_type(self) -> None:
        """Test that struct types are converted to JSON strings."""
        table = pa.Table.from_pydict(
            {
                "id": [1, 2],
                "metadata": [{"key": "value1"}, {"key": "value2"}],
            }
        )

        result = CsvExporter._flatten_for_csv(table)

        assert pa.types.is_string(result.schema.field("metadata").type)
        metadata_list = result.column("metadata").to_pylist()
        assert json.loads(metadata_list[0]) == {"key": "value1"}
        assert json.loads(metadata_list[1]) == {"key": "value2"}

    def test_flatten_null_values(self) -> None:
        """Test that null values in complex types are handled."""
        table = pa.Table.from_pydict(
            {
                "id": [1, 2],
                "tags": [["a", "b"], None],
            }
        )

        result = CsvExporter._flatten_for_csv(table)

        tags_list = result.column("tags").to_pylist()
        # Compact JSON format (no spaces) per centralized serialization
        assert tags_list[0] == '["a","b"]'
        assert tags_list[1] is None


@pytest.mark.unit
class TestCsvExporterExport:
    """Tests for export method."""

    @pytest.mark.asyncio
    async def test_export_creates_file(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> None:
        """Test that export creates the CSV file."""
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)
        table = pa.Table.from_pydict(
            {
                "id": [1, 2],
                "name": ["a", "b"],
            }
        )

        result_path = await exporter.export("test_table", table)

        assert result_path.exists()
        assert result_path == tmp_path / "test_table.csv"

    @pytest.mark.asyncio
    async def test_export_creates_parent_directories(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> None:
        """Test that export creates parent directories if needed."""
        nested_path = tmp_path / "nested" / "path"
        exporter = CsvExporter(base_path=str(nested_path), logger=mock_logger)
        table = pa.Table.from_pydict({"id": [1]})

        result_path = await exporter.export("table", table)

        assert result_path.exists()
        assert nested_path.exists()

    @pytest.mark.asyncio
    async def test_export_with_custom_delimiter(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> None:
        """Test export with custom delimiter."""
        exporter = CsvExporter(
            base_path=str(tmp_path), logger=mock_logger, delimiter=";"
        )
        table = pa.Table.from_pydict(
            {
                "id": [1, 2],
                "name": ["a", "b"],
            }
        )

        result_path = await exporter.export("test", table)

        content = result_path.read_text()
        assert ";" in content
        # PyArrow may quote string headers
        assert '"id";"name"' in content or "id;name" in content

    @pytest.mark.asyncio
    async def test_export_without_header(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> None:
        """Test export without header row."""
        exporter = CsvExporter(
            base_path=str(tmp_path), logger=mock_logger, header=False
        )
        table = pa.Table.from_pydict(
            {
                "id": [1],
                "name": ["test"],
            }
        )

        result_path = await exporter.export("test", table)

        content = result_path.read_text()
        assert "id" not in content
        assert "name" not in content
        assert "1" in content
        assert "test" in content

    @pytest.mark.asyncio
    async def test_export_complex_types(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> None:
        """Test that complex types are properly serialized to JSON."""
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)
        table = pa.Table.from_pydict(
            {
                "id": [1],
                "tags": [["tag1", "tag2"]],
                "metadata": [{"key": "value"}],
            }
        )

        result_path = await exporter.export("test", table)

        content = result_path.read_text()
        # CSV escapes inner quotes with double-quotes, so check for the tag content
        assert "tag1" in content and "tag2" in content
        assert "key" in content and "value" in content

    @pytest.mark.asyncio
    async def test_export_appends_to_existing_file(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> None:
        """Test that export appends to existing file by default."""
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)

        # First export
        table1 = pa.Table.from_pydict({"id": [1], "value": ["first"]})
        await exporter.export("test", table1)

        # Second export (default: append=True)
        table2 = pa.Table.from_pydict({"id": [2], "value": ["second"]})
        result_path = await exporter.export("test", table2)

        content = result_path.read_text()
        assert "first" in content
        assert "second" in content

    @pytest.mark.asyncio
    async def test_export_overwrites_when_append_false(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> None:
        """Test that export overwrites existing file when append=False."""
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)

        # First export
        table1 = pa.Table.from_pydict({"id": [1], "value": ["first"]})
        await exporter.export("test", table1)

        # Second export with append=False
        table2 = pa.Table.from_pydict({"id": [2], "value": ["second"]})
        result_path = await exporter.export("test", table2, append=False)

        content = result_path.read_text()
        assert "second" in content
        assert "first" not in content


@pytest.mark.unit
class TestCsvExporterClear:
    """Tests for CsvExporter.clear() method."""

    def test_csv_exporter_clear__clear_specific_table__ffd56ab7(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> None:
        """Test clearing a specific table's CSV file."""
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)

        # Create test files
        (tmp_path / "table1.csv").write_text("data1")
        (tmp_path / "table1.csv.raw").write_text("raw1")
        (tmp_path / "table2.csv").write_text("data2")

        deleted = exporter.clear("table1")

        assert set(deleted) == {
            tmp_path / "table1.csv",
            tmp_path / "table1.csv.raw",
        }
        assert not (tmp_path / "table1.csv").exists()
        assert not (tmp_path / "table1.csv.raw").exists()
        assert (tmp_path / "table2.csv").exists()

    def test_clear_orphan_raw_sidecar_for_named_table(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> None:
        """Named clear removes a leftover .csv.raw even when CSV is gone."""
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)
        orphan = tmp_path / "records.csv.raw"
        orphan.write_text("id\n1\n", encoding="utf-8")

        deleted = exporter.clear("records")

        assert deleted == [orphan]
        assert not orphan.exists()

    def test_clear_all_csv_files(self, tmp_path: Path, mock_logger: MagicMock) -> None:
        """Test clearing all CSV files."""
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)

        # Create test files
        (tmp_path / "table1.csv").write_text("data1")
        (tmp_path / "table2.csv").write_text("data2")
        (tmp_path / "orphan.csv.raw").write_text("raw")
        (tmp_path / "other.txt").write_text("not csv")

        deleted = exporter.clear()

        assert set(deleted) == {
            tmp_path / "table1.csv",
            tmp_path / "table2.csv",
            tmp_path / "orphan.csv.raw",
        }
        assert not (tmp_path / "table1.csv").exists()
        assert not (tmp_path / "table2.csv").exists()
        assert not (tmp_path / "orphan.csv.raw").exists()
        assert (tmp_path / "other.txt").exists()  # Non-CSV not deleted

    def test_clear_nonexistent_directory(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> None:
        """Test clearing when base_path doesn't exist."""
        exporter = CsvExporter(
            base_path=str(tmp_path / "nonexistent"), logger=mock_logger
        )

        deleted = exporter.clear()

        assert deleted == []

    def test_clear_nonexistent_table(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> None:
        """Test clearing a table that doesn't exist."""
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)

        deleted = exporter.clear("nonexistent")

        assert deleted == []

    def test_clear_locked_file_logs_warning(
        self, tmp_path: Path, mock_logger: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Locked CSV files should be skipped with a warning."""
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)
        locked = tmp_path / "locked.csv"
        locked.write_text("x")

        original_unlink = Path.unlink

        def _patched_unlink(path_obj: Path, *args: object, **kwargs: object) -> None:
            if path_obj == locked:
                raise PermissionError("locked")
            original_unlink(path_obj, *args, **kwargs)

        monkeypatch.setattr(Path, "unlink", _patched_unlink)

        deleted = exporter.clear()

        assert deleted == []
        mock_logger.warning.assert_called()
        assert locked.exists()


@pytest.mark.unit
class TestCsvExporterInternals:
    """Coverage tests for internal branch behavior."""

    def test_sort_table_early_returns(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> None:
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)
        table = pa.Table.from_pydict({"id": [2, 1], "name": ["b", "a"]})

        assert exporter._sort_table(table, []) is table
        assert exporter._sort_table(table, ["missing_column"]) is table

    def test_deduplicate_no_keys_and_missing_keys(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> None:
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)
        table = pa.Table.from_pydict({"id": [1, 1], "name": ["a", "a"]})

        assert exporter._deduplicate(table, []) is table
        assert exporter._deduplicate(table, ["unknown"]) is table
        mock_logger.warning.assert_called()

    def test_deduplicate_logs_removed_rows(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> None:
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)
        table = pa.Table.from_pydict({"id": [1, 1, 2], "name": ["a", "b", "c"]})

        dedup = exporter._deduplicate(table, ["id"])

        assert dedup.num_rows == 2
        mock_logger.debug.assert_called_once()

    def test_deduplicate_handles_import_error(
        self,
        tmp_path: Path,
        mock_logger: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)
        table = pa.Table.from_pydict({"id": [1, 1], "name": ["a", "b"]})
        original_import = builtins.__import__

        def _patched_import(
            name: str,
            globals: object = None,
            locals: object = None,
            fromlist: tuple[str, ...] = (),
            level: int = 0,
        ) -> object:
            if name == "polars":
                raise ImportError("no polars")
            return original_import(name, globals, locals, fromlist, level)

        monkeypatch.setattr(csv_exporter_table_ops, "_builtin_import", _patched_import)
        result = exporter._deduplicate(table, ["id"])

        assert result is table
        mock_logger.warning.assert_called()

    def test_deduplicate_handles_generic_error(
        self,
        tmp_path: Path,
        mock_logger: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)
        table = pa.Table.from_pydict({"id": [1, 1], "name": ["a", "b"]})

        class _BrokenPolarsModule:
            @staticmethod
            def from_arrow(_table: pa.Table) -> object:
                raise RuntimeError("boom")

        monkeypatch.setattr(
            csv_exporter_table_ops,
            "_builtin_import",
            lambda name: (
                _BrokenPolarsModule() if name == "polars" else builtins.__import__(name)
            ),
        )
        result = exporter._deduplicate(table, ["id"])

        assert result is table
        mock_logger.warning.assert_called()

    def test_atomic_csv_write_locked_target_uses_backup(
        self, tmp_path: Path, mock_logger: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)
        table = pa.Table.from_pydict({"id": [1]})
        target = tmp_path / "table.csv"
        write_options = pv.WriteOptions(include_header=True, delimiter=",")
        original_replace = Path.replace
        state = {"raised": False}

        def _patched_replace(path_obj: Path, target_obj: Path) -> Path:
            if target_obj == target and not state["raised"]:
                state["raised"] = True
                raise PermissionError("locked")
            return original_replace(path_obj, target_obj)

        monkeypatch.setattr(csv_exporter_io_ops.os, "name", "posix")
        monkeypatch.setattr(Path, "replace", _patched_replace)

        exporter._atomic_csv_write(table, target, write_options)

        backup_candidates = list(tmp_path.glob("table.write-locked.*.csv"))
        assert len(backup_candidates) == 1
        backup_path = backup_candidates[0]
        expected_digest = hashlib.sha256(backup_path.read_bytes()).hexdigest()[:12]
        assert backup_path.name == f"table.write-locked.{expected_digest}.csv"
        assert backup_path.exists()
        mock_logger.warning.assert_called()

    def test_atomic_csv_write_uses_copy_publish_on_windows(
        self, tmp_path: Path, mock_logger: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)
        table = pa.Table.from_pydict({"id": [1]})
        target = tmp_path / "table.csv"
        write_options = pv.WriteOptions(include_header=True, delimiter=",")

        def _raise_if_replace_called(path_obj: Path, target_obj: Path) -> Path:
            raise AssertionError(f"replace called for {path_obj} -> {target_obj}")

        monkeypatch.setattr(csv_exporter_io_ops.os, "name", "nt")
        monkeypatch.setattr(Path, "replace", _raise_if_replace_called)

        exporter._atomic_csv_write(table, target, write_options)

        assert target.exists()
        assert "id" in target.read_text(encoding="utf-8")

    def test_atomic_csv_write_stages_outside_target_on_windows(
        self, tmp_path: Path, mock_logger: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)
        table = pa.Table.from_pydict({"id": [1]})
        target = tmp_path / "table.csv"
        write_options = pv.WriteOptions(include_header=True, delimiter=",")
        original_mkstemp = tempfile.mkstemp
        observed_dirs: list[object] = []

        def _recording_mkstemp(**kwargs: object) -> tuple[int, str]:
            observed_dirs.append(kwargs.get("dir"))
            return original_mkstemp(
                suffix=str(kwargs["suffix"]),
                prefix=str(kwargs["prefix"]),
            )

        monkeypatch.setattr(csv_exporter_io_ops.os, "name", "nt")
        monkeypatch.setattr(tempfile, "mkstemp", _recording_mkstemp)

        exporter._atomic_csv_write(table, target, write_options)

        assert observed_dirs == [None]
        assert target.exists()

    def test_atomic_csv_write_locked_target_uses_copy_backup_on_windows(
        self, tmp_path: Path, mock_logger: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)
        table = pa.Table.from_pydict({"id": [1]})
        target = tmp_path / "table.csv"
        write_options = pv.WriteOptions(include_header=True, delimiter=",")
        original_copy = csv_exporter_io_ops._copy_csv_payload
        state = {"raised": False}

        def _patched_copy(source_path: Path, target_path: Path) -> None:
            if target_path == target and not state["raised"]:
                state["raised"] = True
                raise PermissionError("locked")
            original_copy(source_path, target_path)

        monkeypatch.setattr(csv_exporter_io_ops.os, "name", "nt")
        monkeypatch.setattr(csv_exporter_io_ops, "_copy_csv_payload", _patched_copy)

        exporter._atomic_csv_write(table, target, write_options)

        backup_candidates = list(tmp_path.glob("table.write-locked.*.csv"))
        assert len(backup_candidates) == 1
        backup_path = backup_candidates[0]
        expected_digest = hashlib.sha256(backup_path.read_bytes()).hexdigest()[:12]
        assert backup_path.name == f"table.write-locked.{expected_digest}.csv"
        assert backup_path.exists()
        mock_logger.warning.assert_called()

    def test_atomic_csv_write_cleans_temp_on_failure(
        self, tmp_path: Path, mock_logger: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)
        table = pa.Table.from_pydict({"id": [1]})
        target = tmp_path / "table.csv"
        write_options = pv.WriteOptions(include_header=True, delimiter=",")
        temp_path = tmp_path / "known_temp.csv.tmp"

        def _fake_mkstemp(**kwargs: object) -> tuple[int, str]:
            fd = os.open(temp_path, os.O_CREAT | os.O_RDWR)
            return fd, str(temp_path)

        def _raise_write_failed(*args: object, **kwargs: object) -> object:
            raise RuntimeError("write failed")

        monkeypatch.setattr(tempfile, "mkstemp", _fake_mkstemp)
        monkeypatch.setattr(
            pv,
            "write_csv",
            _raise_write_failed,
        )

        with pytest.raises(RuntimeError, match="write failed"):
            exporter._atomic_csv_write(table, target, write_options)

        assert not temp_path.exists()


@pytest.mark.unit
class TestCsvExporterTrueAppend:
    """Tests for true file-append behavior (no read-back on append)."""

    @pytest.mark.asyncio
    async def test_append_does_not_read_existing_csv(
        self, tmp_path: Path, mock_logger: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Append path must NOT call pv.read_csv — it only appends new rows."""
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)

        # First write creates the file
        table1 = pa.Table.from_pydict({"id": [1], "name": ["a"]})
        await exporter.export("test", table1)

        # Patch pv.read_csv to detect if it's called during append
        read_called = False
        original_read_csv = pv.read_csv

        def _spy_read_csv(*args: object, **kwargs: object) -> pa.Table:
            nonlocal read_called
            read_called = True
            return original_read_csv(*args, **kwargs)

        monkeypatch.setattr(pv, "read_csv", _spy_read_csv)

        # Second write — append path
        table2 = pa.Table.from_pydict({"id": [2], "name": ["b"]})
        await exporter.export("test", table2)

        assert not read_called, "append path must not read the existing CSV"

        # Both records present
        content = (tmp_path / "test.csv").read_text()
        assert "a" in content
        assert "b" in content

    @pytest.mark.asyncio
    async def test_append_multiple_batches_preserves_all_rows(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> None:
        """Multiple appends accumulate all rows without data loss."""
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)

        for i in range(5):
            table = pa.Table.from_pydict({"id": [i], "val": [f"v{i}"]})
            await exporter.export("multi", table)

        with (tmp_path / "multi.csv").open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))

        assert rows == [{"id": str(i), "val": f"v{i}"} for i in range(5)]

    @pytest.mark.asyncio
    async def test_append_locked_published_csv_does_not_claim_success(
        self, tmp_path: Path, mock_logger: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Locked published CSV after raw append fails closed (backup is not success)."""
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)

        table1 = pa.Table.from_pydict({"id": [1]})
        await exporter.export("locked_test", table1)
        published = tmp_path / "locked_test.csv"
        before = published.read_bytes()
        raw = tmp_path / "locked_test.csv.raw"
        before_raw = raw.read_bytes()

        original_open = open

        def _patched_open(path: object, mode: str = "r", **kwargs: object) -> object:
            if str(path).endswith("locked_test.csv") and "b" in mode and "a" in mode:
                raise PermissionError("locked")
            return original_open(path, mode, **kwargs)

        monkeypatch.setattr("builtins.open", _patched_open)

        table2 = pa.Table.from_pydict({"id": [2]})
        with pytest.raises(
            RuntimeError, match="backup-only publish is not a successful"
        ):
            await exporter.export("locked_test", table2)

        mock_logger.warning.assert_called()
        assert published.read_bytes() == before
        assert raw.read_bytes() == before_raw
        backups = list(tmp_path.glob("locked_test.append-locked.*.csv"))
        assert len(backups) == 1

    @pytest.mark.asyncio
    async def test_append_locked_raw_sidecar_leaves_published_unchanged(
        self, tmp_path: Path, mock_logger: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A locked raw append must not mutate either file or leak a raw CSV backup."""
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)
        await exporter.export("locked_raw", pa.Table.from_pydict({"id": [1]}))
        published = tmp_path / "locked_raw.csv"
        raw = tmp_path / "locked_raw.csv.raw"
        before_published = published.read_bytes()
        before_raw = raw.read_bytes()

        original_open = open

        def _patched_open(path: object, mode: str = "r", **kwargs: object) -> object:
            if str(path).endswith("locked_raw.csv.raw") and "b" in mode and "a" in mode:
                raise PermissionError("locked")
            return original_open(path, mode, **kwargs)

        monkeypatch.setattr("builtins.open", _patched_open)

        with pytest.raises(
            RuntimeError, match="backup-only publish is not a successful"
        ):
            await exporter.export("locked_raw", pa.Table.from_pydict({"id": [2]}))

        assert published.read_bytes() == before_published
        assert raw.read_bytes() == before_raw
        assert not list(tmp_path.glob("*.append-locked.*.csv"))

    @pytest.mark.asyncio
    async def test_overwrite_rejects_header_collision_before_touching_raw(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> None:
        """Colliding spreadsheet-safe headers must not replace an existing pair."""
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)
        await exporter.export(
            "headers",
            pa.Table.from_pydict({"id": [1], "name": ["a"]}),
            append=False,
        )
        published = tmp_path / "headers.csv"
        raw = tmp_path / "headers.csv.raw"
        before_published = published.read_bytes()
        before_raw = raw.read_bytes()

        with pytest.raises(ValueError, match="Spreadsheet-safe column names collide"):
            await exporter.export(
                "headers",
                pa.Table.from_pydict({"=x": [1], "'=x": [2]}),
                append=False,
            )

        assert published.read_bytes() == before_published
        assert raw.read_bytes() == before_raw


@pytest.mark.unit
class TestCsvExporterFinalize:
    """Tests for finalize_csv one-shot dedup+sort."""

    @pytest.mark.asyncio
    async def test_finalize_csv_deduplicates_and_sorts(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> None:
        """finalize_csv must deduplicate by PK and sort."""
        exporter = CsvExporter(
            base_path=str(tmp_path), logger=mock_logger, sort_by=["id"]
        )

        # Write 3 batches with duplicates
        for batch in ([3, 1], [2, 1], [3, 2]):
            table = pa.Table.from_pydict({"id": batch, "val": [f"v{x}" for x in batch]})
            await exporter.export("dedup", table)

        # Finalize with dedup + sort
        result_path = await exporter.finalize_csv("dedup", primary_keys=["id"])

        assert result_path is not None
        result = pv.read_csv(result_path)
        ids = result.column("id").to_pylist()
        # Deduplicated (3 unique ids) and sorted ascending
        assert ids == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_finalize_csv_nonexistent_file_returns_none(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> None:
        """finalize_csv returns None when CSV file does not exist."""
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)

        result = await exporter.finalize_csv("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_finalize_csv_sort_only(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> None:
        """finalize_csv sorts without dedup when no primary_keys."""
        exporter = CsvExporter(
            base_path=str(tmp_path), logger=mock_logger, sort_by=["id"]
        )

        table = pa.Table.from_pydict({"id": [3, 1, 2], "val": ["c", "a", "b"]})
        await exporter.export("sortonly", table, append=False)

        result_path = await exporter.finalize_csv("sortonly")

        assert result_path is not None
        result = pv.read_csv(result_path)
        assert result.column("id").to_pylist() == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_finalize_csv_logs_info(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> None:
        """finalize_csv logs info message with row count."""
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)

        table = pa.Table.from_pydict({"id": [1, 2]})
        await exporter.export("info_test", table, append=False)
        await exporter.finalize_csv("info_test")

        mock_logger.info.assert_called_with(
            "csv_export_finalized",
            table_name="info_test",
            rows=2,
            deduplicated=False,
            sorted=False,
        )

    @pytest.mark.asyncio
    async def test_finalize_csv_dedupes_on_pre_neutralized_primary_keys(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> None:
        """Published CSV is safe; raw sidecar keeps =x and '=x distinct for dedupe."""
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)
        table = pa.Table.from_pydict(
            {"id": ["=x", "'=x"], "val": ["formula", "escaped"]}
        )
        await exporter.export("keys", table, append=False)

        published = tmp_path / "keys.csv"
        raw = published.with_name(f"{published.name}.raw")
        intermediate = pv.read_csv(published)
        assert intermediate.column("id").to_pylist() == ["'=x", "'=x"]
        assert pv.read_csv(raw).column("id").to_pylist() == ["=x", "'=x"]

        result_path = await exporter.finalize_csv("keys", primary_keys=["id"])
        assert result_path is not None
        result = pv.read_csv(result_path)
        assert result.num_rows == 2
        assert set(result.column("val").to_pylist()) == {"formula", "escaped"}
        # Neutralization maps both keys to the same text, but both rows remain.
        assert result.column("id").to_pylist() == ["'=x", "'=x"]

    @pytest.mark.asyncio
    async def test_export_finalize_cycles_keep_formula_keys_then_append(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> None:
        """Two export/finalize cycles plus append keep =x, '=x, and z (3 rows)."""
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)
        first = pa.Table.from_pydict(
            {"id": ["=x", "'=x"], "val": ["formula", "escaped"]}
        )
        await exporter.export("keys", first, append=False)
        assert (tmp_path / "keys.csv").read_text(encoding="utf-8").count("=x") >= 1
        assert '"=x"' not in (tmp_path / "keys.csv").read_text(encoding="utf-8")

        first_path = await exporter.finalize_csv("keys", primary_keys=["id"])
        assert first_path is not None
        assert pv.read_csv(first_path).num_rows == 2

        second_path = await exporter.finalize_csv("keys", primary_keys=["id"])
        assert second_path is not None
        after_second = pv.read_csv(second_path)
        assert after_second.num_rows == 2
        assert set(after_second.column("val").to_pylist()) == {"formula", "escaped"}

        await exporter.export(
            "keys",
            pa.Table.from_pydict({"id": ["z"], "val": ["plain"]}),
            append=True,
        )
        third_path = await exporter.finalize_csv("keys", primary_keys=["id"])
        assert third_path is not None
        final = pv.read_csv(third_path)
        assert final.num_rows == 3
        assert set(final.column("val").to_pylist()) == {
            "formula",
            "escaped",
            "plain",
        }
        assert set(
            pv.read_csv(third_path.with_name(f"{third_path.name}.raw"))
            .column("id")
            .to_pylist()
        ) == {
            "=x",
            "'=x",
            "z",
        }


@pytest.mark.unit
class TestCsvExporterPathConfinement:
    """table_name must not escape the export directory (Sonar AaHT3lBY8IZ3BlS9H5SG)."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "evil_name",
        [
            "../escape",
            "..\\escape",
            "/tmp/escape",
            "nested/escape",
            "nested\\escape",
            ".",
            "..",
            "",
            "   ",
            "a/../../b",
        ],
    )
    async def test_export_rejects_path_traversal_table_names(
        self,
        tmp_path: Path,
        mock_logger: MagicMock,
        evil_name: str,
    ) -> None:
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)
        table = pa.Table.from_pydict({"id": [1]})
        outside_before = {
            path.resolve() for path in tmp_path.parent.glob("*") if path.is_file()
        }

        with pytest.raises(ValueError, match="CSV export|table name"):
            await exporter.export(evil_name, table, append=False)

        outside_after = {
            path.resolve() for path in tmp_path.parent.glob("*") if path.is_file()
        }
        assert outside_after == outside_before
        assert list(tmp_path.glob("*")) == []

    @pytest.mark.asyncio
    async def test_append_seed_raw_sidecar_stays_inside_export_root(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> None:
        """Legacy published-only CSV seeds ``.csv.raw`` only under the export root."""
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)
        published = tmp_path / "legacy.csv"
        published.write_text("id\n1\n", encoding="utf-8")

        await exporter.export(
            "legacy",
            pa.Table.from_pydict({"id": [2]}),
            append=True,
        )

        raw = published.with_name(f"{published.name}.raw")
        assert raw.is_file()
        assert raw.resolve().is_relative_to(tmp_path.resolve())
        assert published.resolve().is_relative_to(tmp_path.resolve())
        assert set(pv.read_csv(raw).column("id").to_pylist()) == {1, 2}
        # Published path remains spreadsheet-safe for newly appended rows.
        assert set(pv.read_csv(published).column("id").to_pylist()) == {1, 2}

    def test_resolve_table_export_paths_allows_dotted_table_names(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> None:
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)
        csv_path, raw_path = exporter._resolve_table_export_paths("chembl.activity")
        assert csv_path.name == "chembl.activity.csv"
        assert raw_path.name == "chembl.activity.csv.raw"
        assert csv_path.parent == tmp_path.resolve()
        assert raw_path.parent == tmp_path.resolve()

    @pytest.mark.parametrize(
        "evil_name",
        [
            "../escape",
            "..\\escape",
            "/tmp/escape",
            "nested/escape",
            "a/../../b",
        ],
    )
    def test_seed_raw_sidecar_rejects_path_traversal_table_names(
        self,
        tmp_path: Path,
        evil_name: str,
    ) -> None:
        """Seed sink rebuilds paths from table_name; traversal must not touch IO."""
        outside_before = {
            path.resolve() for path in tmp_path.parent.glob("*") if path.is_file()
        }
        with pytest.raises(ValueError, match="CSV export|table name"):
            _seed_raw_sidecar_if_missing(base_path=tmp_path, table_name=evil_name)
        outside_after = {
            path.resolve() for path in tmp_path.parent.glob("*") if path.is_file()
        }
        assert outside_after == outside_before
        assert list(tmp_path.glob("*")) == []


@pytest.mark.asyncio
async def test_failed_published_overwrite_restores_pair_before_resume(
    tmp_path, mock_logger, monkeypatch
):
    from bioetl.infrastructure.export import csv_exporter_io_ops as io

    exporter = CsvExporter(str(tmp_path), mock_logger)
    await exporter.export("pair", pa.table({"id": [1]}), append=False)
    published = tmp_path / "pair.csv"
    raw = tmp_path / "pair.csv.raw"
    before = {published: published.read_bytes(), raw: raw.read_bytes()}
    original = io._publish_csv_payload

    def publish(source, target):
        if target == published:
            raise PermissionError("published locked")
        return original(source, target)

    with monkeypatch.context() as patch:
        patch.setattr(io, "_publish_csv_payload", publish)
        with pytest.raises(RuntimeError, match="backup-only"):
            await exporter.export("pair", pa.table({"id": [2]}), append=False)
    assert {path: path.read_bytes() for path in before} == before
    await exporter.export("pair", pa.table({"id": [3]}))
    await exporter.finalize_csv("pair")
    assert pv.read_csv(published)["id"].to_pylist() == [1, 3]


@pytest.mark.asyncio
@pytest.mark.parametrize("table_name", ["pair", None])
async def test_failed_published_clear_keeps_raw_identity(
    tmp_path, mock_logger, monkeypatch, table_name
):
    exporter = CsvExporter(str(tmp_path), mock_logger)
    await exporter.export("pair", pa.table({"key": ["=x", "'=x"], "id": [1, 2]}))
    published = tmp_path / "pair.csv"
    raw = tmp_path / "pair.csv.raw"
    before = {published: published.read_bytes(), raw: raw.read_bytes()}
    original = Path.unlink

    def unlink(path, *args, **kwargs):
        if path == published:
            raise PermissionError("published locked")
        return original(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", unlink)
        assert exporter.clear(table_name) == []
    assert {path: path.read_bytes() for path in before} == before
    await exporter.finalize_csv("pair", primary_keys=["key"], sort_by=["id"])
    assert pv.read_csv(published)["id"].to_pylist() == [1, 2]
