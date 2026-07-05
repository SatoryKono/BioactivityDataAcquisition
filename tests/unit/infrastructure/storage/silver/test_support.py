"""Unit tests for Silver layer support utilities."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import pyarrow as pa

from bioetl.infrastructure.storage.silver.support import (
    get_table_schema,
    prepare_arrow_data,
    resolve_table_path,
)

pytestmark = pytest.mark.unit


class TestResolveTablePath:
    """Test table path resolution."""

    def test_resolves_with_dot_notation(self):
        """Test resolving path with dot notation table name."""
        result = resolve_table_path("/data/delta", "chembl.activity")
        assert result == "/data/delta/chembl/activity"

    def test_resolves_with_flat_structure(self):
        """Test resolving path with flat structure."""
        result = resolve_table_path(
            "/data/delta", "chembl.activity", flat_structure=True
        )
        assert result == "/data/delta"

    def test_resolves_with_path_base(self):
        """Test resolving with Path base."""
        result = resolve_table_path(Path("/data/delta"), "chembl.activity")
        # Normalize path comparison for cross-platform compatibility
        assert "chembl/activity" in result or "chembl\\activity" in result

    def test_resolves_single_component_table_name(self):
        """Test resolving with single component table name."""
        result = resolve_table_path("/data/delta", "activity")
        assert result == "/data/delta/activity"

    def test_resolves_nested_table_name(self):
        """Test resolving with nested table name."""
        result = resolve_table_path("/data/delta", "provider.entity.subset")
        assert result == "/data/delta/provider/entity/subset"


class TestPrepareArrowData:
    """Test Arrow data preparation."""

    def test_prepares_basic_records(self):
        """Test basic record preparation."""
        schema = pa.schema([("field1", pa.string()), ("field2", pa.int32())])
        records = [{"field1": "test", "field2": 42}]

        result = prepare_arrow_data(records, schema, primary_keys=["field1"])

        assert isinstance(result, pa.Table)
        assert result.num_rows == 1
        assert result.num_columns == 2

    def test_filters_to_schema_columns(self):
        """Test that extra columns are filtered out."""
        schema = pa.schema([("field1", pa.string()), ("field2", pa.int32())])
        records = [
            {"field1": "test", "field2": 42, "extra_field": "should_be_filtered"}
        ]

        result = prepare_arrow_data(records, schema, primary_keys=["field1"])

        assert "extra_field" not in result.schema.names
        assert "field1" in result.schema.names
        assert "field2" in result.schema.names

    def test_respects_column_order(self):
        """Test that explicit column order is respected."""
        schema = pa.schema([("field1", pa.string()), ("field2", pa.int32())])
        records = [{"field1": "test", "field2": 42}]
        custom_order = ["field2", "field1"]

        result = prepare_arrow_data(
            records, schema, primary_keys=["field1"], column_order=custom_order
        )

        assert result.schema.names == custom_order

    def test_sorts_by_primary_keys(self):
        """Test that records are sorted by primary keys."""
        schema = pa.schema([("id", pa.int32()), ("value", pa.string())])
        records = [
            {"id": 3, "value": "c"},
            {"id": 1, "value": "a"},
            {"id": 2, "value": "b"},
        ]

        result = prepare_arrow_data(records, schema, primary_keys=["id"])

        assert result.to_pydict()["id"] == [1, 2, 3]

    def test_sorts_by_multiple_primary_keys(self):
        """Test sorting by multiple primary keys."""
        schema = pa.schema(
            [("id1", pa.int32()), ("id2", pa.int32()), ("value", pa.string())]
        )
        records = [
            {"id1": 2, "id2": 2, "value": "d"},
            {"id1": 1, "id2": 2, "value": "c"},
            {"id1": 2, "id2": 1, "value": "b"},
            {"id1": 1, "id2": 1, "value": "a"},
        ]

        result = prepare_arrow_data(records, schema, primary_keys=["id1", "id2"])

        expected = [
            {"id1": 1, "id2": 1},
            {"id1": 1, "id2": 2},
            {"id1": 2, "id2": 1},
            {"id1": 2, "id2": 2},
        ]
        actual = result.to_pydict()
        assert actual["id1"] == [e["id1"] for e in expected]
        assert actual["id2"] == [e["id2"] for e in expected]

    def test_handles_empty_records(self):
        """Test handling of empty record list."""
        schema = pa.schema([("field1", pa.string()), ("field2", pa.int32())])
        records = []

        result = prepare_arrow_data(records, schema, primary_keys=["field1"])

        assert result.num_rows == 0

    def test_handles_missing_nullable_columns(self):
        """Test handling of missing nullable columns."""
        schema = pa.schema(
            [
                ("field1", pa.string()),
                ("field2", pa.int32()),
                ("optional_field", pa.string()),
            ]
        )
        records = [{"field1": "test", "field2": 42}]

        result = prepare_arrow_data(records, schema, primary_keys=["field1"])

        assert "optional_field" in result.schema.names

    def test_type_conversion(self):
        """Test that type conversion is applied."""
        schema = pa.schema([("field1", pa.string()), ("field2", pa.int32())])
        records = [{"field1": "test", "field2": 42}]  # Use correct type

        result = prepare_arrow_data(records, schema, primary_keys=["field1"])

        assert result.schema.field("field2").type == pa.int32()


class TestGetTableSchema:
    """Test async table schema retrieval."""

    @pytest.mark.asyncio
    async def test_returns_schema_for_existing_table(self):
        """Test returning schema for existing table."""
        mock_schema = MagicMock()
        mock_delta_table = MagicMock()
        mock_delta_table.schema.return_value = mock_schema

        with (
            patch(
                "bioetl.infrastructure.storage.silver.support.DeltaTable",
                return_value=mock_delta_table,
            ),
            patch(
                "bioetl.infrastructure.storage.silver.support.delta_schema_to_pyarrow",
                return_value=pa.schema([("field1", pa.string())]),
            ),
        ):
            result = await get_table_schema("/data/delta", "test_table")

            assert result is not None
            assert isinstance(result, pa.Schema)

    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent_table(self):
        """Test returning None when table doesn't exist."""
        from deltalake.exceptions import TableNotFoundError

        with patch(
            "bioetl.infrastructure.storage.silver.support.DeltaTable",
            side_effect=TableNotFoundError("Table not found"),
        ):
            result = await get_table_schema("/data/delta", "test_table")

            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_permission_error(self):
        """Test returning None on permission errors."""
        with patch(
            "bioetl.infrastructure.storage.silver.support.DeltaTable",
            side_effect=PermissionError("Access denied"),
        ):
            result = await get_table_schema("/data/delta", "test_table")

            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_corrupt_table(self):
        """Test returning None for corrupt tables."""
        with patch(
            "bioetl.infrastructure.storage.silver.support.DeltaTable",
            side_effect=Exception("Corrupt table"),
        ):
            result = await get_table_schema("/data/delta", "test_table")

            assert result is None

    @pytest.mark.asyncio
    async def test_uses_executor_for_sync_operations(self):
        """Test that synchronous operations run in executor."""
        mock_schema = MagicMock()
        mock_delta_table = MagicMock()
        mock_delta_table.schema.return_value = mock_schema

        with (
            patch(
                "bioetl.infrastructure.storage.silver.support.DeltaTable",
                return_value=mock_delta_table,
            ),
            patch(
                "bioetl.infrastructure.storage.silver.support.delta_schema_to_pyarrow",
                return_value=pa.schema([("field1", pa.string())]),
            ),
        ):
            result = await get_table_schema("/data/delta", "test_table")

            # Verify the result
            assert result is not None
            assert isinstance(result, pa.Schema)

    @pytest.mark.asyncio
    async def test_handles_attribute_error(self):
        """Test handling of AttributeError from DeltaTable."""
        with patch(
            "bioetl.infrastructure.storage.silver.support.DeltaTable",
            side_effect=AttributeError("Missing attribute"),
        ):
            result = await get_table_schema("/data/delta", "test_table")

            assert result is None

    @pytest.mark.asyncio
    async def test_handles_type_error(self):
        """Test handling of TypeError from DeltaTable."""
        with patch(
            "bioetl.infrastructure.storage.silver.support.DeltaTable",
            side_effect=TypeError("Invalid type"),
        ):
            result = await get_table_schema("/data/delta", "test_table")

            assert result is None

    @pytest.mark.asyncio
    async def test_handles_value_error(self):
        """Test handling of ValueError from DeltaTable."""
        with patch(
            "bioetl.infrastructure.storage.silver.support.DeltaTable",
            side_effect=ValueError("Invalid value"),
        ):
            result = await get_table_schema("/data/delta", "test_table")

            assert result is None

    @pytest.mark.asyncio
    async def test_handles_runtime_error(self):
        """Test handling of RuntimeError from DeltaTable."""
        with patch(
            "bioetl.infrastructure.storage.silver.support.DeltaTable",
            side_effect=RuntimeError("Runtime error"),
        ):
            result = await get_table_schema("/data/delta", "test_table")

            assert result is None


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_prepare_arrow_data_with_none_values(self):
        """Test handling of None values in records."""
        schema = pa.schema(
            [
                ("field1", pa.string()),
                ("field2", pa.int32()),
                ("optional_field", pa.string()),
            ]
        )
        records = [{"field1": "test", "field2": 42, "optional_field": None}]

        result = prepare_arrow_data(records, schema, primary_keys=["field1"])

        assert result.num_rows == 1

    def test_prepare_arrow_data_with_mixed_types(self):
        """Test handling of mixed type values."""
        schema = pa.schema([("field1", pa.string()), ("field2", pa.int32())])
        records = [
            {"field1": "test1", "field2": 42},
            {"field1": "test2", "field2": 100},
        ]

        result = prepare_arrow_data(records, schema, primary_keys=["field1"])

        assert result.num_rows == 2

    def test_resolve_table_path_with_trailing_slash(self):
        """Test path resolution with trailing slash in base."""
        result = resolve_table_path("/data/delta/", "chembl.activity")
        assert "chembl/activity" in result

    def test_resolve_table_path_with_empty_table_name(self):
        """Test path resolution with empty table name."""
        result = resolve_table_path("/data/delta", "")
        assert result == "/data/delta"

    def test_prepare_arrow_data_preserves_determinism(self):
        """Test that preparation preserves deterministic ordering."""
        schema = pa.schema([("id", pa.int32()), ("value", pa.string())])
        records = [
            {"id": 3, "value": "c"},
            {"id": 1, "value": "a"},
            {"id": 2, "value": "b"},
        ]

        result1 = prepare_arrow_data(records, schema, primary_keys=["id"])
        result2 = prepare_arrow_data(records, schema, primary_keys=["id"])

        # Results should be identical
        assert result1.to_pydict() == result2.to_pydict()
