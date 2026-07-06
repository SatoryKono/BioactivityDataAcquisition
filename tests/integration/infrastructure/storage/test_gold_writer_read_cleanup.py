"""Integration tests for GoldWriterReadCleanupMixin."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from bioetl.infrastructure.storage.gold.read_cleanup_mixin import (
    GoldWriterReadCleanupMixin,
    _build_read_projection,
    _load_gold_writer_module,
)

pytestmark = pytest.mark.integration


class ConcreteGoldReaderForTest(GoldWriterReadCleanupMixin):
    """Concrete implementation for testing the mixin."""

    def __init__(self, base_path: str) -> None:
        self._base_path = base_path

    def _resolve_table_path(self, table_name: str) -> str:
        return f"{self._base_path}/{table_name}"

    async def _run_in_executor(self, fn, *args):
        return fn(*args)


class TestLoadGoldWriterModule:
    """Tests for _load_gold_writer_module."""

    def test_loads_module(self) -> None:
        """Should load the gold_writer module."""
        module = _load_gold_writer_module()
        assert isinstance(module, ModuleType)
        assert module.__name__ == "bioetl.infrastructure.storage.gold_writer"


class TestBuildReadProjection:
    """Tests for read projection helper."""

    def test_returns_none_without_requested_columns(self) -> None:
        """No projection should be applied when caller wants full records."""
        assert _build_read_projection(columns=None, current_only=True) is None

    def test_returns_none_when_current_only(self) -> None:
        """Current-only reads read full rows first for filtering, then project."""
        assert _build_read_projection(
            columns=["entity_id"],
            current_only=True,
        ) is None

    def test_returns_none_when_current_only_with_is_current(self) -> None:
        """Current-only reads read full rows first even when is_current is requested."""
        assert _build_read_projection(
            columns=["entity_id", "is_current"],
            current_only=True,
        ) is None


class TestPreviewCleanup:
    """Tests for preview_cleanup."""

    def test_preview_nonexistent_path(self, tmp_path: Path) -> None:
        """Should report non-existent path correctly."""
        reader = ConcreteGoldReaderForTest(str(tmp_path / "nonexistent"))
        result = reader.preview_cleanup("my_table")

        assert result["exists"] is False
        assert result["file_count"] == 0
        assert result["layer"] == "gold"
        assert result["table_name"] == "my_table"

    def test_preview_existing_path_with_files(self, tmp_path: Path) -> None:
        """Should count files in existing table directory."""
        table_dir = tmp_path / "my_table"
        table_dir.mkdir()
        (table_dir / "file1.parquet").write_text("data")
        (table_dir / "file2.parquet").write_text("data")
        sub = table_dir / "subdir"
        sub.mkdir()
        (sub / "file3.parquet").write_text("data")

        reader = ConcreteGoldReaderForTest(str(tmp_path))
        result = reader.preview_cleanup("my_table")

        assert result["exists"] is True
        assert result["file_count"] == 3
        assert result["layer"] == "gold"

    def test_preview_empty_directory(self, tmp_path: Path) -> None:
        """Should return file_count=0 for empty directory."""
        table_dir = tmp_path / "empty_table"
        table_dir.mkdir()

        reader = ConcreteGoldReaderForTest(str(tmp_path))
        result = reader.preview_cleanup("empty_table")

        assert result["exists"] is True
        assert result["file_count"] == 0


class TestReadGold:
    """Tests for read_gold async method."""

    @pytest.mark.asyncio
    async def test_read_gold_basic(self, tmp_path: Path) -> None:
        """Should read data from Gold table via DeltaTable mock."""
        reader = ConcreteGoldReaderForTest(str(tmp_path))

        mock_arrow_table = MagicMock()
        mock_arrow_table.column_names = ["entity_id", "value"]
        mock_arrow_table.to_pylist.return_value = [
            {"entity_id": "E1", "value": 1.0},
            {"entity_id": "E2", "value": 2.0},
        ]

        mock_dt = MagicMock()
        mock_dt.to_pyarrow_table.return_value = mock_arrow_table

        mock_module = MagicMock()
        mock_module.DeltaTable.return_value = mock_dt

        with patch(
            "bioetl.infrastructure.storage.gold.read_cleanup_mixin._load_gold_writer_module",
            return_value=mock_module,
        ):
            result = await reader.read_gold("test_table")

        assert len(result) == 2
        assert result[0]["entity_id"] == "E1"

    @pytest.mark.asyncio
    async def test_read_gold_with_columns_filter(self, tmp_path: Path) -> None:
        """Should filter columns when specified."""
        reader = ConcreteGoldReaderForTest(str(tmp_path))

        mock_arrow_table = MagicMock()
        mock_arrow_table.column_names = ["entity_id", "value", "extra"]
        mock_arrow_table.to_pylist.return_value = [
            {"entity_id": "E1", "value": 1.0, "extra": "x"},
        ]

        mock_dt = MagicMock()
        mock_dt.to_pyarrow_table.return_value = mock_arrow_table

        mock_module = MagicMock()
        mock_module.DeltaTable.return_value = mock_dt

        with patch(
            "bioetl.infrastructure.storage.gold.read_cleanup_mixin._load_gold_writer_module",
            return_value=mock_module,
        ):
            result = await reader.read_gold("test_table", columns=["entity_id"])

        assert len(result) == 1
        assert "entity_id" in result[0]
        assert "extra" not in result[0]
        # When current_only=True (default), projection is None to allow filtering
        mock_dt.to_pyarrow_table.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_read_gold_with_columns_filter_current_only_false(
        self, tmp_path: Path
    ) -> None:
        """Should apply projection when current_only=False."""
        reader = ConcreteGoldReaderForTest(str(tmp_path))

        mock_arrow_table = MagicMock()
        mock_arrow_table.column_names = ["entity_id", "value", "extra"]
        mock_arrow_table.to_pylist.return_value = [
            {"entity_id": "E1", "value": 1.0, "extra": "x"},
        ]

        mock_dt = MagicMock()
        mock_dt.to_pyarrow_table.return_value = mock_arrow_table

        mock_module = MagicMock()
        mock_module.DeltaTable.return_value = mock_dt

        with patch(
            "bioetl.infrastructure.storage.gold.read_cleanup_mixin._load_gold_writer_module",
            return_value=mock_module,
        ):
            result = await reader.read_gold(
                "test_table", columns=["entity_id"], current_only=False
            )

        assert len(result) == 1
        assert "entity_id" in result[0]
        assert "extra" not in result[0]
        # When current_only=False, projection is applied directly
        mock_dt.to_pyarrow_table.assert_called_once_with(["entity_id"])

    @pytest.mark.asyncio
    async def test_read_gold_filters_is_current(self, tmp_path: Path) -> None:
        """Should filter by is_current=True when column exists and current_only=True."""
        import pyarrow as pa

        reader = ConcreteGoldReaderForTest(str(tmp_path))

        arrow_table = pa.table(
            {
                "entity_id": ["E1", "E2"],
                "is_current": [True, False],
            }
        )

        mock_dt = MagicMock()
        mock_dt.to_pyarrow_table.return_value = arrow_table

        mock_module = MagicMock()
        mock_module.DeltaTable.return_value = mock_dt

        with patch(
            "bioetl.infrastructure.storage.gold.read_cleanup_mixin._load_gold_writer_module",
            return_value=mock_module,
        ):
            result = await reader.read_gold("test_table", current_only=True)

        assert len(result) == 1
        assert result[0]["entity_id"] == "E1"
        assert result[0]["is_current"] is True
        mock_dt.to_pyarrow_table.assert_called_once_with()


class TestGetHistory:
    """Tests for get_history async method."""

    @pytest.mark.asyncio
    async def test_get_history_basic(self, tmp_path: Path) -> None:
        """Should return history records."""
        reader = ConcreteGoldReaderForTest(str(tmp_path))

        mock_arrow_table = MagicMock()
        mock_arrow_table.column_names = ["entity_id", "value"]
        mock_arrow_table.to_pylist.return_value = [
            {"entity_id": "E1", "value": 1.0},
            {"entity_id": "E1", "value": 2.0},
        ]

        mock_dt = MagicMock()
        mock_dt.to_pyarrow_table.return_value = mock_arrow_table

        mock_module = MagicMock()
        mock_module.DeltaTable.return_value = mock_dt

        with patch(
            "bioetl.infrastructure.storage.gold.read_cleanup_mixin._load_gold_writer_module",
            return_value=mock_module,
        ):
            result = await reader.get_history("test_table")

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_history_with_limit(self, tmp_path: Path) -> None:
        """Should respect limit parameter."""
        reader = ConcreteGoldReaderForTest(str(tmp_path))

        records = [{"entity_id": f"E{i}"} for i in range(20)]
        mock_arrow_table = MagicMock()
        mock_arrow_table.column_names = ["entity_id"]
        mock_arrow_table.to_pylist.return_value = records

        mock_dt = MagicMock()
        mock_dt.to_pyarrow_table.return_value = mock_arrow_table

        mock_module = MagicMock()
        mock_module.DeltaTable.return_value = mock_dt

        with patch(
            "bioetl.infrastructure.storage.gold.read_cleanup_mixin._load_gold_writer_module",
            return_value=mock_module,
        ):
            result = await reader.get_history("test_table", limit=5)

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_get_history_limit_zero_returns_all(self, tmp_path: Path) -> None:
        """limit=0 should return all records."""
        reader = ConcreteGoldReaderForTest(str(tmp_path))

        records = [{"entity_id": f"E{i}"} for i in range(5)]
        mock_arrow_table = MagicMock()
        mock_arrow_table.column_names = ["entity_id"]
        mock_arrow_table.to_pylist.return_value = records

        mock_dt = MagicMock()
        mock_dt.to_pyarrow_table.return_value = mock_arrow_table

        mock_module = MagicMock()
        mock_module.DeltaTable.return_value = mock_dt

        with patch(
            "bioetl.infrastructure.storage.gold.read_cleanup_mixin._load_gold_writer_module",
            return_value=mock_module,
        ):
            result = await reader.get_history("test_table", limit=0)

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_get_history_sorts_by_valid_from(self, tmp_path: Path) -> None:
        """Should sort by valid_from when column exists."""
        reader = ConcreteGoldReaderForTest(str(tmp_path))

        mock_arrow_table = MagicMock()
        mock_arrow_table.column_names = ["entity_id", "valid_from"]
        sorted_table = MagicMock()
        sorted_table.column_names = ["entity_id", "valid_from"]
        sorted_table.to_pylist.return_value = [{"entity_id": "E1"}]
        mock_arrow_table.sort_by.return_value = sorted_table

        mock_dt = MagicMock()
        mock_dt.to_pyarrow_table.return_value = mock_arrow_table

        mock_module = MagicMock()
        mock_module.DeltaTable.return_value = mock_dt

        with patch(
            "bioetl.infrastructure.storage.gold.read_cleanup_mixin._load_gold_writer_module",
            return_value=mock_module,
        ):
            await reader.get_history("test_table")

        mock_arrow_table.sort_by.assert_called_once_with([("valid_from", "ascending")])

    @pytest.mark.asyncio
    async def test_get_history_with_business_key_filter(self, tmp_path: Path) -> None:
        """Should filter by business key values."""
        import pyarrow as pa

        reader = ConcreteGoldReaderForTest(str(tmp_path))

        arrow_table = pa.table(
            {
                "entity_id": ["E1", "E2", "E1"],
                "value": [1.0, 2.0, 3.0],
            }
        )

        mock_dt = MagicMock()
        mock_dt.to_pyarrow_table.return_value = arrow_table

        mock_module = MagicMock()
        mock_module.DeltaTable.return_value = mock_dt

        with patch(
            "bioetl.infrastructure.storage.gold.read_cleanup_mixin._load_gold_writer_module",
            return_value=mock_module,
        ):
            result = await reader.get_history(
                "test_table",
                business_key_values={"entity_id": "E1"},
            )

        assert len(result) == 2
        assert all(r["entity_id"] == "E1" for r in result)
