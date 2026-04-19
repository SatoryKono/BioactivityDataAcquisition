"""Unit tests for CsvExporter."""

from __future__ import annotations

import builtins
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pyarrow as pa
import pyarrow.csv as pv
import pytest

import bioetl.infrastructure.export.csv_exporter_table_ops as csv_exporter_table_ops
from bioetl.infrastructure.export.csv_exporter import CsvExporter


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger for tests."""
    return MagicMock()


@pytest.mark.unit
class TestCsvExporterInit:
    """Tests for CsvExporter initialization."""

    def test_init_with_defaults(self, tmp_path: Path, mock_logger: MagicMock) -> None:
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

    def test_clear_specific_table(self, tmp_path: Path, mock_logger: MagicMock) -> None:
        """Test clearing a specific table's CSV file."""
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)

        # Create test files
        (tmp_path / "table1.csv").write_text("data1")
        (tmp_path / "table2.csv").write_text("data2")

        deleted = exporter.clear("table1")

        assert len(deleted) == 1
        assert not (tmp_path / "table1.csv").exists()
        assert (tmp_path / "table2.csv").exists()

    def test_clear_all_csv_files(self, tmp_path: Path, mock_logger: MagicMock) -> None:
        """Test clearing all CSV files."""
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)

        # Create test files
        (tmp_path / "table1.csv").write_text("data1")
        (tmp_path / "table2.csv").write_text("data2")
        (tmp_path / "other.txt").write_text("not csv")

        deleted = exporter.clear()

        assert len(deleted) == 2
        assert not (tmp_path / "table1.csv").exists()
        assert not (tmp_path / "table2.csv").exists()
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

        monkeypatch.setattr(Path, "replace", _patched_replace)
        monkeypatch.setattr("time.time", lambda: 1234567890)

        exporter._atomic_csv_write(table, target, write_options)

        backup_path = tmp_path / "table.1234567890.csv"
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

        result = pv.read_csv(tmp_path / "multi.csv")
        assert result.num_rows == 5

    @pytest.mark.asyncio
    async def test_append_locked_target_writes_backup(
        self, tmp_path: Path, mock_logger: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If target CSV is locked during append, batch goes to backup file."""
        exporter = CsvExporter(base_path=str(tmp_path), logger=mock_logger)

        table1 = pa.Table.from_pydict({"id": [1]})
        await exporter.export("locked_test", table1)

        # Make the open() call raise PermissionError for the target file
        original_open = open

        def _patched_open(path: object, mode: str = "r", **kwargs: object) -> object:
            if str(path).endswith("locked_test.csv") and "b" in mode and "a" in mode:
                raise PermissionError("locked")
            return original_open(path, mode, **kwargs)

        monkeypatch.setattr("builtins.open", _patched_open)
        monkeypatch.setattr("time.time", lambda: 9999999999)

        table2 = pa.Table.from_pydict({"id": [2]})
        await exporter.export("locked_test", table2)

        mock_logger.warning.assert_called()
        backup = tmp_path / "locked_test.9999999999.csv"
        assert backup.exists()


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
