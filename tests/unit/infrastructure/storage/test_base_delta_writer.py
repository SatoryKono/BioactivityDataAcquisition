"""Tests for BaseDeltaWriter functionality.

Tests the common Delta Lake writer functionality including
Arrow data preparation, primary key sorting, and table management.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pyarrow as pa
import pytest
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.infrastructure.storage.base_delta_writer import (
    BaseDeltaWriter,
    _get_string_fields,
    _serialize_value,
)


@pytest.mark.unit
class TestSerializeValue:
    """Test _serialize_value function."""

    def test_writer_serialize_value__value_returns_none__6458b76a(self) -> None:
        """Test that None value returns None."""
        assert _serialize_value(None, is_string_field=True) is None
        assert _serialize_value(None, is_string_field=False) is None

    def test_dict_to_json_string(self) -> None:
        """Test dictionary serialization to JSON string for string fields."""
        value = {"key": "value", "num": 123}
        result = _serialize_value(value, is_string_field=True)
        assert isinstance(result, str)
        assert "key" in result
        assert "value" in result

    def test_list_to_json_string(self) -> None:
        """Test list serialization to JSON string for string fields."""
        value = [1, 2, 3]
        result = _serialize_value(value, is_string_field=True)
        assert isinstance(result, str)
        assert "[1,2,3]" in result

    def test_dict_not_serialized_for_non_string_field(self) -> None:
        """Test dictionary is returned as-is for non-string fields."""
        value = {"key": "value"}
        result = _serialize_value(value, is_string_field=False)
        assert result == value

    def test_scalar_values_unchanged(self) -> None:
        """Test scalar values are returned unchanged."""
        assert _serialize_value("hello", is_string_field=True) == "hello"
        assert _serialize_value(123, is_string_field=False) == 123
        assert _serialize_value(45.67, is_string_field=False) == pytest.approx(45.67)

    def test_json_sorted_keys(self) -> None:
        """Test JSON serialization uses sorted keys for determinism."""
        value = {"b": 2, "a": 1}
        result = _serialize_value(value, is_string_field=True)
        # Verify a comes before b in the output
        assert result.index("a") < result.index("b")


@pytest.mark.unit
class TestGetStringFields:
    """Test _get_string_fields function."""

    def test_extracts_string_fields(self) -> None:
        """Test extraction of string type fields from schema."""
        schema = pa.schema(
            [
                pa.field("id", pa.string()),
                pa.field("count", pa.int64()),
                pa.field("name", pa.string()),
            ]
        )
        result = _get_string_fields(schema)
        assert result == {"id", "name"}

    def test_extracts_large_string_fields(self) -> None:
        """Test extraction of large_string type fields."""
        schema = pa.schema(
            [
                pa.field("description", pa.large_string()),
                pa.field("value", pa.float64()),
            ]
        )
        result = _get_string_fields(schema)
        assert result == {"description"}

    def test_empty_schema_returns_empty_set(self) -> None:
        """Test empty schema returns empty set."""
        schema = pa.schema([])
        result = _get_string_fields(schema)
        assert result == set()

    def test_no_string_fields(self) -> None:
        """Test schema with no string fields."""
        schema = pa.schema(
            [
                pa.field("id", pa.int64()),
                pa.field("value", pa.float64()),
            ]
        )
        result = _get_string_fields(schema)
        assert result == set()


@pytest.mark.unit
class TestBaseDeltaWriter:
    """Test BaseDeltaWriter class."""

    @pytest.fixture
    def mock_logger(self) -> MagicMock:
        """Create a mock logger."""
        return MagicMock()

    @pytest.fixture
    def writer(self, tmp_path: Path, mock_logger: MagicMock) -> BaseDeltaWriter:
        """Create a BaseDeltaWriter instance."""
        return BaseDeltaWriter(
            base_path=tmp_path,
            logger=mock_logger,
        )

    def test_base_delta_writer__initialization__57222f35(
        self, writer: BaseDeltaWriter, tmp_path: Path
    ) -> None:
        """Test writer initialization."""
        assert writer.base_path == str(tmp_path)
        assert writer.logger is not None
        assert writer._retention_manager is not None

    def test_base_path_strips_trailing_slash(
        self,
        tmp_path: Path,
        mock_logger: MagicMock,
    ) -> None:
        """Test that trailing slashes are stripped from base_path."""
        writer = BaseDeltaWriter(
            base_path=f"{tmp_path}/",
            logger=mock_logger,
        )
        assert not writer.base_path.endswith("/")

    def test_get_table_path__delta_writer__constructs_expected_path(
        self,
        writer: BaseDeltaWriter,
        tmp_path: Path,
    ) -> None:
        """Test get_table_path method constructs expected path for delta writer."""
        path = writer.get_table_path("chembl.activity")
        assert path == tmp_path / "chembl" / "activity"

    def test_get_table_path_single_level(
        self,
        writer: BaseDeltaWriter,
        tmp_path: Path,
    ) -> None:
        """Test get_table_path with single-level name."""
        path = writer.get_table_path("activity")
        assert path == tmp_path / "activity"

    def test_prepare_arrow_data(self, writer: BaseDeltaWriter) -> None:
        """Test _prepare_arrow_data method."""
        records: list[dict[str, Any]] = [
            {"id": "1", "name": "test", "extra": "ignored"},
            {"id": "2", "name": "test2"},
        ]
        schema = pa.schema(
            [
                pa.field("id", pa.string()),
                pa.field("name", pa.string()),
            ]
        )

        result = writer._prepare_arrow_data(
            records=records,
            schema=schema,
            primary_keys=["id"],
        )

        assert isinstance(result, pa.Table)
        assert result.num_rows == 2
        assert set(result.column_names) == {"id", "name"}

    def test_prepare_arrow_data_with_json_serialization(
        self,
        writer: BaseDeltaWriter,
    ) -> None:
        """Test _prepare_arrow_data serializes dicts to JSON for string fields."""
        records: list[dict[str, Any]] = [
            {"id": "1", "metadata": {"key": "value"}},
        ]
        schema = pa.schema(
            [
                pa.field("id", pa.string()),
                pa.field("metadata", pa.string()),
            ]
        )

        result = writer._prepare_arrow_data(
            records=records,
            schema=schema,
            primary_keys=[],
        )

        # Verify metadata was serialized to JSON string
        metadata_col = result.column("metadata")
        assert "key" in str(metadata_col[0])

    def test_sort_by_primary_keys(self, writer: BaseDeltaWriter) -> None:
        """Test _sort_by_primary_keys method."""
        table = pa.table(
            {
                "id": ["c", "a", "b"],
                "value": [3, 1, 2],
            }
        )

        result = writer._sort_by_primary_keys(
            table=table,
            primary_keys=["id"],
            schema_names=["id", "value"],
        )

        # Verify sorted by id
        ids = result.column("id").to_pylist()
        assert ids == ["a", "b", "c"]

    def test_sort_by_primary_keys_empty_keys(self, writer: BaseDeltaWriter) -> None:
        """Test _sort_by_primary_keys with empty primary keys."""
        table = pa.table({"id": ["c", "a", "b"]})
        result = writer._sort_by_primary_keys(
            table=table,
            primary_keys=[],
            schema_names=["id"],
        )
        # Should return unchanged
        assert result.column("id").to_pylist() == ["c", "a", "b"]

    def test_sort_by_primary_keys_invalid_key(
        self,
        writer: BaseDeltaWriter,
        mock_logger: MagicMock,
    ) -> None:
        """Test _sort_by_primary_keys with invalid key logs warning."""
        table = pa.table({"id": ["c", "a", "b"]})
        result = writer._sort_by_primary_keys(
            table=table,
            primary_keys=["nonexistent"],
            schema_names=["id"],
        )
        # Should return unchanged and log warning
        assert result.column("id").to_pylist() == ["c", "a", "b"]
        mock_logger.warning.assert_called_once()

    def test_clear_nonexistent_base_path(
        self,
        mock_logger: MagicMock,
    ) -> None:
        """Test clear with nonexistent base path returns 0."""
        writer = BaseDeltaWriter(
            base_path="/nonexistent/path",
            logger=mock_logger,
        )
        result = writer.clear()
        assert result == 0

    def test_clear_nonexistent_table__test_base_delta_writer_infrastructure_storage_test_base_delta_writer_268(
        self,
        tmp_path: Path,
        mock_logger: MagicMock,
    ) -> None:
        """Test clear nonexistent table returns 0."""
        writer = BaseDeltaWriter(base_path=tmp_path, logger=mock_logger)
        result = writer.clear(table_name="nonexistent")
        assert result == 0


@pytest.mark.unit
@pytest.mark.asyncio
class TestBaseDeltaWriterAsync:
    """Test async methods of BaseDeltaWriter."""

    @pytest.fixture
    def mock_logger(self) -> MagicMock:
        """Create a mock logger."""
        return MagicMock()

    @pytest.fixture
    def writer(self, tmp_path: Path, mock_logger: MagicMock) -> BaseDeltaWriter:
        """Create a BaseDeltaWriter instance."""
        return BaseDeltaWriter(
            base_path=tmp_path,
            logger=mock_logger,
        )

    async def test_get_table_schema_nonexistent(
        self,
        writer: BaseDeltaWriter,
    ) -> None:
        """Test _get_table_schema returns None for nonexistent table."""
        result = await writer._get_table_schema("nonexistent_table")
        assert result is None

    async def test_read_table_raises_file_not_found_for_missing_table(
        self,
        writer: BaseDeltaWriter,
    ) -> None:
        """Test read_table raises FileNotFoundError when table is missing."""
        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            with pytest.raises(FileNotFoundError, match="missing_table"):
                await writer.read_table("missing_table")

    async def test_read_table_returns_pylist_records(
        self,
        writer: BaseDeltaWriter,
    ) -> None:
        """Test read_table returns record dictionaries from the shared loader path."""
        expected_records = [{"id": "1", "name": "test"}]
        mock_batch = MagicMock()
        mock_batch.to_pylist.return_value = expected_records
        mock_reader = [mock_batch]
        mock_scanner = MagicMock()
        mock_scanner.to_reader.return_value = mock_reader
        mock_dataset = MagicMock()
        mock_dataset.scanner.return_value = mock_scanner

        mock_delta_table = MagicMock()
        mock_delta_table.to_pyarrow_dataset.return_value = mock_dataset

        with patch(
            "bioetl.infrastructure.storage.delta.table_ops."
            "_can_use_pyarrow_dataset_scanner",
            return_value=True,
        ), patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            return_value=mock_delta_table,
        ):
            result = await writer.read_table("existing_table", columns=["id", "name"])

        assert result == expected_records
        mock_dataset.scanner.assert_called_once_with(columns=["id", "name"])

    async def test_read_table_falls_back_to_arrow_table_when_dataset_reader_missing(
        self,
        writer: BaseDeltaWriter,
    ) -> None:
        """Fallback to legacy full-table conversion when scanner reader is unavailable."""
        expected_records = [{"id": "1", "name": "test"}]
        mock_arrow_table = MagicMock()
        mock_arrow_table.to_pylist.return_value = expected_records
        mock_scanner = MagicMock()
        del mock_scanner.to_reader
        mock_dataset = MagicMock()
        mock_dataset.scanner.return_value = mock_scanner
        mock_delta_table = MagicMock()
        mock_delta_table.to_pyarrow_dataset.return_value = mock_dataset
        mock_delta_table.to_pyarrow_table.return_value = mock_arrow_table

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            return_value=mock_delta_table,
        ):
            result = await writer.read_table("existing_table", columns=["id", "name"])

        assert result == expected_records
        mock_delta_table.to_pyarrow_table.assert_called_once_with(
            columns=["id", "name"]
        )
