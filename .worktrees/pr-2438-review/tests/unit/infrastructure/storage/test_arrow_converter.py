"""Unit tests for ArrowDataConverter.

Tests the Arrow table conversion utilities extracted from GoldWriter.
"""

from __future__ import annotations

import pyarrow as pa
import pytest

from bioetl.infrastructure.storage.arrow_converter import ArrowDataConverter


class TestArrowDataConverterSanitizeType:
    """Tests for type sanitization for Delta Lake compatibility."""

    def test_sanitize_null_type_to_string(self) -> None:
        """Null type should be converted to string."""
        converter = ArrowDataConverter()
        result = converter.sanitize_type_for_delta(pa.null())
        assert result == pa.string()

    def test_sanitize_list_of_null_to_list_of_string(self) -> None:
        """List<null> should become list<string>."""
        converter = ArrowDataConverter()
        result = converter.sanitize_type_for_delta(pa.list_(pa.null()))
        assert result == pa.list_(pa.string())

    def test_sanitize_large_list_of_null(self) -> None:
        """Large list<null> should become large_list<string>."""
        converter = ArrowDataConverter()
        result = converter.sanitize_type_for_delta(pa.large_list(pa.null()))
        assert result == pa.large_list(pa.string())

    def test_sanitize_struct_with_null_field(self) -> None:
        """Struct with null field should have field converted to string."""
        converter = ArrowDataConverter()
        struct_type = pa.struct(
            [
                pa.field("name", pa.string()),
                pa.field("value", pa.null()),
            ]
        )
        result = converter.sanitize_type_for_delta(struct_type)
        expected = pa.struct(
            [
                pa.field("name", pa.string()),
                pa.field("value", pa.string()),
            ]
        )
        assert result == expected

    def test_sanitize_map_with_null_value(self) -> None:
        """Map with null value type should have value converted to string."""
        converter = ArrowDataConverter()
        map_type = pa.map_(pa.string(), pa.null())
        result = converter.sanitize_type_for_delta(map_type)
        assert result == pa.map_(pa.string(), pa.string())

    def test_sanitize_primitive_types_unchanged(self) -> None:
        """Primitive types (non-null) should remain unchanged."""
        converter = ArrowDataConverter()
        types_to_test = [
            pa.int64(),
            pa.float64(),
            pa.string(),
            pa.bool_(),
            pa.date32(),
            pa.timestamp("us"),
        ]
        for dtype in types_to_test:
            result = converter.sanitize_type_for_delta(dtype)
            assert result == dtype, f"Type {dtype} should remain unchanged"


class TestArrowDataConverterConvertRecords:
    """Tests for record to Arrow table conversion."""

    def test_convert_simple_records(self) -> None:
        """Should convert simple records to Arrow table."""
        converter = ArrowDataConverter()
        records = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]
        result = converter.convert_records_to_arrow(records)
        assert isinstance(result, pa.Table)
        assert len(result) == 2
        assert "id" in result.schema.names
        assert "name" in result.schema.names

    def test_convert_records_with_primary_keys_sorts(self) -> None:
        """Should sort records by primary keys for deterministic writes."""
        converter = ArrowDataConverter()
        records = [
            {"id": 3, "name": "Charlie"},
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]
        result = converter.convert_records_to_arrow(records, primary_keys=["id"])
        ids = result.column("id").to_pylist()
        assert ids == [1, 2, 3], "Records should be sorted by primary key"

    def test_convert_records_with_null_values(self) -> None:
        """Should handle records with null values."""
        converter = ArrowDataConverter()
        records = [
            {"id": 1, "name": "Alice", "email": None},
            {"id": 2, "name": "Bob", "email": "bob@example.com"},
        ]
        result = converter.convert_records_to_arrow(records)
        assert len(result) == 2
        emails = result.column("email").to_pylist()
        assert emails[0] is None
        assert emails[1] == "bob@example.com"

    def test_convert_empty_records(self) -> None:
        """Should handle empty record list."""
        converter = ArrowDataConverter()
        records: list[dict[str, object]] = []
        result = converter.convert_records_to_arrow(records)
        assert isinstance(result, pa.Table)
        assert len(result) == 0

    def test_convert_records_with_invalid_primary_key_ignored(self) -> None:
        """Should ignore primary keys that don't exist in schema."""
        converter = ArrowDataConverter()
        records = [
            {"id": 2, "name": "Bob"},
            {"id": 1, "name": "Alice"},
        ]
        # 'nonexistent' key doesn't exist but should be silently ignored
        result = converter.convert_records_to_arrow(
            records, primary_keys=["nonexistent", "id"]
        )
        ids = result.column("id").to_pylist()
        assert ids == [1, 2], "Should still sort by valid primary key 'id'"


class TestArrowDataConverterNullColumnSanitization:
    """Tests for sanitizing null-typed columns in tables."""

    def test_sanitize_all_null_column(self) -> None:
        """Column with all null values should become string type."""
        converter = ArrowDataConverter()
        records = [
            {"id": 1, "optional": None},
            {"id": 2, "optional": None},
        ]
        result = converter.convert_records_to_arrow(records)
        # The column should be string type (sanitized from null)
        optional_field = result.schema.field("optional")
        assert optional_field.type == pa.string()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
