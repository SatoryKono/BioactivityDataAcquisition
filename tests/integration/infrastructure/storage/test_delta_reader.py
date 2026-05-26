"""Integration tests for DeltaReader.

Tests the read-only Delta Lake table accessor with column projection,
row limiting, schema retrieval, and existence checks.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pyarrow as pa
import pytest

import bioetl.infrastructure.storage.delta_reader as delta_reader_module
from bioetl.infrastructure.storage.delta_reader import DeltaReader


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger."""
    return MagicMock()


@pytest.fixture
def reader(tmp_path: Path, mock_logger: MagicMock) -> DeltaReader:
    """Create a DeltaReader instance."""
    return DeltaReader(base_path=tmp_path, logger=mock_logger)


class _FakeDeltaSchema:
    def __init__(self, schema: pa.Schema) -> None:
        self._schema = schema

    def to_arrow(self) -> pa.Schema:
        return self._schema


class _FakeDeltaScanner:
    def __init__(self, table: pa.Table) -> None:
        self._table = table

    def head(self, limit: int) -> pa.Table:
        return self._table.slice(0, max(0, limit))


class _FakeDeltaDataset:
    def __init__(self, table: pa.Table) -> None:
        self._table = table

    def scanner(self, columns: list[str] | None = None) -> _FakeDeltaScanner:
        table = self._table.select(columns) if columns is not None else self._table
        return _FakeDeltaScanner(table)


@pytest.fixture(autouse=True)
def fake_delta_tables(monkeypatch: pytest.MonkeyPatch) -> dict[str, pa.Table]:
    """Patch delta-rs table access with deterministic read-only fixtures.

    These tests validate ``DeltaReader`` semantics, not delta-rs writer behavior.
    Avoiding native writer/reader filesystem work keeps Windows setup deterministic
    while still exercising ``DeltaReader`` path resolution and async wrappers.
    """
    registry: dict[str, pa.Table] = {}

    class _FakeDeltaTable:
        def __init__(self, table_uri: str) -> None:
            self._table_uri = str(Path(table_uri))
            try:
                self._table = registry[self._table_uri]
            except KeyError as exc:
                raise delta_reader_module.DeltaTableNotFoundError(table_uri) from exc

        def count(self) -> int:
            return self._table.num_rows

        def schema(self) -> _FakeDeltaSchema:
            return _FakeDeltaSchema(self._table.schema)

        def to_pyarrow_dataset(self) -> _FakeDeltaDataset:
            return _FakeDeltaDataset(self._table)

        def to_pyarrow_table(self, columns: list[str] | None = None) -> pa.Table:
            if columns is None:
                return self._table
            return self._table.select(columns)

    monkeypatch.setattr(delta_reader_module, "DeltaTable", _FakeDeltaTable)
    return registry


def _register_delta_table(
    table_path: Path, table: pa.Table, registry: dict[str, pa.Table]
) -> None:
    table_path.mkdir(parents=True, exist_ok=True)
    (table_path / "_delta_log").mkdir(exist_ok=True)
    registry[str(table_path)] = table


@pytest.fixture
def sample_delta_table(tmp_path: Path, fake_delta_tables: dict[str, pa.Table]) -> Path:
    """Create a sample Delta table for testing.

    Returns:
        Path to the created Delta table.
    """
    table_path = tmp_path / "test_provider" / "test_entity"
    table_path.mkdir(parents=True)

    table = pa.table(
        {
            "id": ["1", "2", "3"],
            "name": ["Alice", "Bob", "Charlie"],
            "value": [10, 20, 30],
        }
    )

    _register_delta_table(table_path, table, fake_delta_tables)
    return table_path


@pytest.mark.integration
class TestDeltaReaderInit:
    """Test DeltaReader initialization."""

    def test_initialization(self, reader: DeltaReader, tmp_path: Path) -> None:
        """Test reader initializes with correct base path."""
        assert reader._base_path == tmp_path

    def test_base_path_accepts_string(
        self, tmp_path: Path, mock_logger: MagicMock
    ) -> None:
        """Test reader accepts string path."""
        reader = DeltaReader(base_path=str(tmp_path), logger=mock_logger)
        assert reader._base_path == tmp_path


@pytest.mark.integration
class TestResolvePath:
    """Test _resolve_path method."""

    def test_relative_path_resolved_to_base(
        self, reader: DeltaReader, tmp_path: Path
    ) -> None:
        """Test relative path is resolved relative to base_path."""
        result = reader._resolve_path("provider/entity")
        assert result == tmp_path / "provider" / "entity"

    def test_absolute_path_returned_unchanged(
        self, reader: DeltaReader, tmp_path: Path
    ) -> None:
        """Test absolute path is returned as-is."""
        # Use tmp_path to get a valid absolute path on any platform
        absolute_path = str(tmp_path / "some" / "absolute" / "path")
        result = reader._resolve_path(absolute_path)
        assert result == Path(absolute_path)

    def test_nested_relative_path(self, reader: DeltaReader, tmp_path: Path) -> None:
        """Test nested relative path is resolved correctly."""
        result = reader._resolve_path("provider/entity/table")
        assert result == tmp_path / "provider" / "entity" / "table"

    def test_dot_notation_path_resolves_to_provider_entity_path(
        self,
        reader: DeltaReader,
        tmp_path: Path,
    ) -> None:
        """Logical provider.entity names should resolve to nested directories."""
        result = reader._resolve_path("chembl.activity__v2_0_0")
        assert result == tmp_path / "chembl" / "activity__v2_0_0"


@pytest.mark.integration
@pytest.mark.asyncio
class TestReadTable:
    """Test read_table method."""

    async def test_read_table_success(
        self,
        reader: DeltaReader,
        sample_delta_table: Path,
    ) -> None:
        """Test reading table returns PyArrow table."""
        table_path = f"{sample_delta_table.parent.name}/{sample_delta_table.name}"
        result = await reader.read_table(table_path)

        assert isinstance(result, pa.Table)
        assert result.num_rows == 3
        assert set(result.column_names) == {"id", "name", "value"}

    async def test_read_table_with_column_projection(
        self,
        reader: DeltaReader,
        sample_delta_table: Path,
    ) -> None:
        """Test reading table with column projection."""
        table_path = f"{sample_delta_table.parent.name}/{sample_delta_table.name}"
        result = await reader.read_table(table_path, columns=["id", "name"])

        assert result.num_rows == 3
        assert set(result.column_names) == {"id", "name"}

    async def test_read_table_full_read_uses_scanner_head(
        self,
        tmp_path: Path,
        mock_logger: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Full reads should avoid delta-rs to_pyarrow_table native scan hangs."""
        expected = pa.table({"id": ["1", "2"]})
        captured: dict[str, object] = {}

        class _FakeScanner:
            def head(self, limit: int) -> pa.Table:
                captured["limit"] = limit
                return expected

        class _FakeDataset:
            def scanner(self, columns: list[str] | None = None) -> _FakeScanner:
                captured["columns"] = columns
                return _FakeScanner()

        class _FakeDeltaTable:
            def __init__(self, table_uri: str) -> None:
                captured["table_uri"] = table_uri

            def count(self) -> int:
                return expected.num_rows

            def to_pyarrow_dataset(self) -> _FakeDataset:
                return _FakeDataset()

            def to_pyarrow_table(self, columns: list[str] | None = None) -> pa.Table:
                raise AssertionError(f"unexpected full-table read: columns={columns}")

        monkeypatch.setattr(delta_reader_module, "DeltaTable", _FakeDeltaTable)
        reader = DeltaReader(base_path=tmp_path, logger=mock_logger)

        result = await reader.read_table("provider/entity", columns=["id"])

        assert result == expected
        assert captured["columns"] == ["id"]
        assert captured["limit"] == expected.num_rows

    async def test_read_table_full_read_falls_back_to_sentinel_when_count_fails(
        self,
        tmp_path: Path,
        mock_logger: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Full reads should not fall back to scan-based count paths."""
        expected = pa.table({"id": ["1", "2"]})
        captured: dict[str, object] = {}

        class _FakeScanner:
            def head(self, limit: int) -> pa.Table:
                captured["limit"] = limit
                return expected

        class _FakeDataset:
            def scanner(self, columns: list[str] | None = None) -> _FakeScanner:
                captured["columns"] = columns
                return _FakeScanner()

        class _FakeDeltaTable:
            def __init__(self, table_uri: str) -> None:
                captured["table_uri"] = table_uri

            def count(self) -> int:
                raise RuntimeError("native count unavailable")

            def to_pyarrow_dataset(self) -> _FakeDataset:
                return _FakeDataset()

            def to_pyarrow_table(self, columns: list[str] | None = None) -> pa.Table:
                raise AssertionError(f"unexpected full-table read: columns={columns}")

        monkeypatch.setattr(delta_reader_module, "DeltaTable", _FakeDeltaTable)
        reader = DeltaReader(base_path=tmp_path, logger=mock_logger)

        result = await reader.read_table("provider/entity", columns=["id"])

        assert result == expected
        assert captured["columns"] == ["id"]
        assert captured["limit"] == delta_reader_module._FULL_READ_HEAD_LIMIT

    async def test_read_table_with_limit(
        self,
        reader: DeltaReader,
        sample_delta_table: Path,
    ) -> None:
        """Test reading table with row limit."""
        table_path = f"{sample_delta_table.parent.name}/{sample_delta_table.name}"
        result = await reader.read_table(table_path, limit=2)

        assert result.num_rows == 2

    async def test_read_table_limit_larger_than_rows(
        self,
        reader: DeltaReader,
        sample_delta_table: Path,
    ) -> None:
        """Test reading table with limit larger than row count."""
        table_path = f"{sample_delta_table.parent.name}/{sample_delta_table.name}"
        result = await reader.read_table(table_path, limit=100)

        # Should return all rows without error
        assert result.num_rows == 3

    async def test_read_table_with_columns_and_limit(
        self,
        reader: DeltaReader,
        sample_delta_table: Path,
    ) -> None:
        """Test reading table with both column projection and limit."""
        table_path = f"{sample_delta_table.parent.name}/{sample_delta_table.name}"
        result = await reader.read_table(table_path, columns=["id"], limit=1)

        assert result.num_rows == 1
        assert result.column_names == ["id"]

    async def test_read_table_nonexistent_raises_file_not_found(
        self,
        reader: DeltaReader,
    ) -> None:
        """Test reading nonexistent table raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError) as exc_info:
            await reader.read_table("nonexistent/table")

        assert "Delta table not found" in str(exc_info.value)

    async def test_read_table_logs_debug_message(
        self,
        reader: DeltaReader,
        sample_delta_table: Path,
        mock_logger: MagicMock,
    ) -> None:
        """Test reading table logs debug message."""
        table_path = f"{sample_delta_table.parent.name}/{sample_delta_table.name}"
        await reader.read_table(table_path, columns=["id"], limit=2)

        mock_logger.debug.assert_called_once()
        call_kwargs = mock_logger.debug.call_args[1]
        assert call_kwargs["columns"] == ["id"]
        assert call_kwargs["limit"] == 2

    async def test_read_versioned_table_uses_versioned_logical_name(
        self,
        reader: DeltaReader,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Version-aware read should resolve the physical versioned table name."""
        expected = pa.table({"id": ["1"]})
        captured: dict[str, object] = {}

        async def _fake_read_table(
            table_path: str,
            columns: list[str] | None = None,
            limit: int | None = None,
        ) -> pa.Table:
            await asyncio.sleep(0)
            captured["table_path"] = table_path
            captured["columns"] = columns
            captured["limit"] = limit
            return expected

        monkeypatch.setattr(reader, "read_table", _fake_read_table)

        result = await reader.read_versioned_table(
            "chembl.activity",
            "2.0.0",
            columns=["id"],
            limit=1,
        )

        assert result == expected
        assert captured["table_path"] == "chembl.activity__v2_0_0"

    async def test_read_with_fallback_reads_first_existing_candidate(
        self,
        reader: DeltaReader,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Fallback read should skip missing tables and return the next available one."""
        expected = pa.table({"id": ["1"]})

        async def _fake_read_table(
            table_path: str,
            columns: list[str] | None = None,
            limit: int | None = None,
        ) -> pa.Table:
            await asyncio.sleep(0)
            del columns, limit
            if table_path == "chembl.activity__v2_0_0":
                raise FileNotFoundError("missing v2")
            return expected

        monkeypatch.setattr(reader, "read_table", _fake_read_table)

        result = await reader.read_with_fallback(
            "chembl.activity",
            ["2.0.0", "1.0.0"],
        )

        assert result == expected


@pytest.mark.integration
@pytest.mark.asyncio
class TestGetSchema:
    """Test get_schema method."""

    async def test_get_schema_success(
        self,
        reader: DeltaReader,
        sample_delta_table: Path,
    ) -> None:
        """Test getting schema returns schema with expected fields."""
        table_path = f"{sample_delta_table.parent.name}/{sample_delta_table.name}"
        result = await reader.get_schema(table_path)

        # Schema may be pyarrow.Schema or arro3.core.Schema depending on delta-rs version
        assert hasattr(result, "__len__")
        assert len(result) == 3
        field_names = [f.name for f in result]
        assert set(field_names) == {"id", "name", "value"}

    async def test_get_schema_nonexistent_raises_file_not_found(
        self,
        reader: DeltaReader,
    ) -> None:
        """Test getting schema for nonexistent table raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError) as exc_info:
            await reader.get_schema("nonexistent/table")

        assert "Delta table not found" in str(exc_info.value)


@pytest.mark.integration
@pytest.mark.asyncio
class TestGetRowCount:
    """Test get_row_count method."""

    async def test_get_row_count_success(
        self,
        reader: DeltaReader,
        sample_delta_table: Path,
    ) -> None:
        """Test getting row count returns correct count."""
        table_path = f"{sample_delta_table.parent.name}/{sample_delta_table.name}"
        result = await reader.get_row_count(table_path)

        assert result == 3

    async def test_get_row_count_nonexistent_raises_file_not_found(
        self,
        reader: DeltaReader,
    ) -> None:
        """Test getting row count for nonexistent table raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError) as exc_info:
            await reader.get_row_count("nonexistent/table")

        assert "Delta table not found" in str(exc_info.value)

    async def test_get_row_count_prefers_native_count_api(
        self,
        tmp_path: Path,
        mock_logger: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Use DeltaTable.count() when available instead of metadata fallbacks."""

        class _FakeDeltaTable:
            def __init__(self, _table_uri: str) -> None:
                self._table_uri = _table_uri

            def count(self) -> int:
                return 7

            def get_add_actions(self, *, flatten: bool) -> object:
                raise AssertionError(f"unexpected metadata fallback: flatten={flatten}")

        monkeypatch.setattr(delta_reader_module, "DeltaTable", _FakeDeltaTable)
        reader = DeltaReader(base_path=tmp_path, logger=mock_logger)

        result = await reader.get_row_count("provider/entity")

        assert result == 7

    async def test_get_row_count_propagates_keyboard_interrupt(
        self,
        tmp_path: Path,
        mock_logger: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Do not swallow cancellation-style BaseException subclasses."""

        class _FakeDeltaTable:
            def __init__(self, _table_uri: str) -> None:
                self._table_uri = _table_uri

            def count(self) -> int:
                raise KeyboardInterrupt()

        monkeypatch.setattr(delta_reader_module, "DeltaTable", _FakeDeltaTable)
        reader = DeltaReader(base_path=tmp_path, logger=mock_logger)

        with pytest.raises(KeyboardInterrupt):
            await reader.get_row_count("provider/entity")


@pytest.mark.integration
@pytest.mark.asyncio
class TestTableExists:
    """Test table_exists method."""

    async def test_table_exists_returns_true_for_valid_table(
        self,
        reader: DeltaReader,
        sample_delta_table: Path,
    ) -> None:
        """Test table_exists returns True for valid Delta table."""
        table_path = f"{sample_delta_table.parent.name}/{sample_delta_table.name}"
        result = await reader.table_exists(table_path)

        assert result is True

    async def test_table_exists_returns_false_for_nonexistent_directory(
        self,
        reader: DeltaReader,
    ) -> None:
        """Test table_exists returns False for nonexistent directory."""
        result = await reader.table_exists("nonexistent/table")

        assert result is False

    async def test_table_exists_returns_false_for_directory_without_delta_log(
        self,
        reader: DeltaReader,
        tmp_path: Path,
    ) -> None:
        """Test table_exists returns False for directory without _delta_log."""
        # Create a directory without _delta_log
        not_delta = tmp_path / "not_delta"
        not_delta.mkdir()

        result = await reader.table_exists("not_delta")

        assert result is False

    async def test_table_exists_returns_false_for_invalid_delta_log(
        self,
        reader: DeltaReader,
        tmp_path: Path,
    ) -> None:
        """Test table_exists returns False for invalid Delta table."""
        # Create directory with _delta_log but no valid content
        invalid_table = tmp_path / "invalid_table"
        invalid_delta_log = invalid_table / "_delta_log"
        invalid_delta_log.mkdir(parents=True)
        # Create an invalid log file
        (invalid_delta_log / "00000.json").write_text("invalid json")

        result = await reader.table_exists("invalid_table")

        assert result is False


@pytest.mark.integration
@pytest.mark.asyncio
class TestAclose:
    """Test aclose method."""

    async def test_aclose_is_noop(self, reader: DeltaReader) -> None:
        """Test aclose is a no-op and doesn't raise."""
        # Should complete without error
        await reader.aclose()


@pytest.mark.integration
@pytest.mark.asyncio
class TestAbsolutePath:
    """Test reading with absolute paths."""

    async def test_read_table_with_absolute_path(
        self,
        tmp_path: Path,
        mock_logger: MagicMock,
        fake_delta_tables: dict[str, pa.Table],
    ) -> None:
        """Test reading table using absolute path."""
        # Create table at a specific location
        table_path = tmp_path / "absolute" / "table"
        table_path.mkdir(parents=True)
        table = pa.table({"id": ["1", "2"]})
        _register_delta_table(table_path, table, fake_delta_tables)

        # Create reader with different base path
        reader = DeltaReader(base_path=tmp_path / "other", logger=mock_logger)

        # Read using absolute path
        result = await reader.read_table(str(table_path))

        assert result.num_rows == 2

    async def test_table_exists_with_absolute_path(
        self,
        tmp_path: Path,
        mock_logger: MagicMock,
        fake_delta_tables: dict[str, pa.Table],
    ) -> None:
        """Test table_exists using absolute path."""
        # Create table at a specific location
        table_path = tmp_path / "absolute" / "table"
        table_path.mkdir(parents=True)
        table = pa.table({"id": ["1"]})
        _register_delta_table(table_path, table, fake_delta_tables)

        # Create reader with different base path
        reader = DeltaReader(base_path=tmp_path / "other", logger=mock_logger)

        result = await reader.table_exists(str(table_path))

        assert result is True


@pytest.mark.integration
@pytest.mark.asyncio
class TestEmptyTable:
    """Test reading empty Delta tables."""

    async def test_read_empty_table(
        self,
        tmp_path: Path,
        mock_logger: MagicMock,
        fake_delta_tables: dict[str, pa.Table],
    ) -> None:
        """Test reading an empty Delta table."""
        table_path = tmp_path / "empty_table"
        table_path.mkdir(parents=True)

        # Create empty table with schema
        schema = pa.schema(
            [
                pa.field("id", pa.string()),
                pa.field("value", pa.int64()),
            ]
        )
        empty_table = pa.table({"id": [], "value": []}, schema=schema)
        _register_delta_table(table_path, empty_table, fake_delta_tables)

        reader = DeltaReader(base_path=tmp_path, logger=mock_logger)
        result = await reader.read_table("empty_table")

        assert result.num_rows == 0
        assert set(result.column_names) == {"id", "value"}

    async def test_get_row_count_empty_table(
        self,
        tmp_path: Path,
        mock_logger: MagicMock,
        fake_delta_tables: dict[str, pa.Table],
    ) -> None:
        """Test getting row count for empty table."""
        table_path = tmp_path / "empty_table"
        table_path.mkdir(parents=True)

        schema = pa.schema([pa.field("id", pa.string())])
        empty_table = pa.table({"id": []}, schema=schema)
        _register_delta_table(table_path, empty_table, fake_delta_tables)

        reader = DeltaReader(base_path=tmp_path, logger=mock_logger)
        result = await reader.get_row_count("empty_table")

        assert result == 0


@pytest.mark.integration
@pytest.mark.asyncio
class TestLimitEdgeCases:
    """Test edge cases for limit parameter."""

    async def test_limit_zero_returns_empty(
        self,
        reader: DeltaReader,
        sample_delta_table: Path,
    ) -> None:
        """Test limit=0 returns empty table."""
        table_path = f"{sample_delta_table.parent.name}/{sample_delta_table.name}"
        result = await reader.read_table(table_path, limit=0)

        assert result.num_rows == 0

    async def test_limit_none_returns_all(
        self,
        reader: DeltaReader,
        sample_delta_table: Path,
    ) -> None:
        """Test limit=None returns all rows."""
        table_path = f"{sample_delta_table.parent.name}/{sample_delta_table.name}"
        result = await reader.read_table(table_path, limit=None)

        assert result.num_rows == 3
