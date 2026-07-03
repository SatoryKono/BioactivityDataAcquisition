"""Unit tests for ArrowDataConverter.

Tests the Arrow table conversion utilities extracted from GoldWriter.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pyarrow as pa
import pytest

from bioetl.infrastructure.storage.delta.arrow_converter import (
    ArrowDataConverter,
    build_arrow_schema_preparation_context,
    filter_record_for_schema,
    get_string_fields,
    serialize_value_for_arrow_schema,
    sort_arrow_table_by_primary_keys,
)

pytestmark = pytest.mark.unit


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

    def test_convert_records_can_preserve_original_column_order(self) -> None:
        """Raw conversion should skip canonical ordering when explicitly requested."""
        converter = ArrowDataConverter()
        records = [{"name": "Alice", "_run_id": "run-1", "id": 1}]

        result = converter.convert_records_to_arrow(
            records,
            apply_column_order=False,
        )

        assert result.column_names == ["name", "_run_id", "id"]

    def test_convert_empty_records(self) -> None:
        """Should handle empty record list."""
        converter = ArrowDataConverter()
        records: list[dict[str, object]] = []
        result = converter.convert_records_to_arrow(records)
        assert isinstance(result, pa.Table)
        assert len(result) == 0
        assert result.column_names == []

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

    def test_convert_records_with_schema_filters_unknown_fields(self) -> None:
        """Schema-aware conversion should drop fields absent from the target schema."""
        converter = ArrowDataConverter()
        schema = pa.schema(
            [
                pa.field("id", pa.string()),
                pa.field("payload", pa.string()),
            ]
        )
        result = converter.convert_records_to_arrow_with_schema(
            [
                {
                    "id": "1",
                    "payload": {"a": 1},
                    "ignored": "drop-me",
                }
            ],
            schema,
        )

        assert result.column_names == ["id", "payload"]
        assert "ignored" not in result.column_names
        assert result.column("payload").to_pylist() == ['{"a":1}']

    def test_convert_records_with_schema_sorts_by_primary_keys(self) -> None:
        """Schema-aware conversion should preserve deterministic primary-key sort."""
        converter = ArrowDataConverter()
        schema = pa.schema(
            [
                pa.field("id", pa.int64()),
                pa.field("payload", pa.string()),
            ]
        )

        result = converter.convert_records_to_arrow_with_schema(
            [
                {"id": 3, "payload": {"name": "c"}},
                {"id": 1, "payload": {"name": "a"}},
                {"id": 2, "payload": {"name": "b"}},
            ],
            schema,
            primary_keys=["id"],
        )

        assert result.column("id").to_pylist() == [1, 2, 3]

    def test_convert_records_with_schema_preserves_schema_order_by_default(
        self,
    ) -> None:
        """Schema-aware conversion should keep schema order unless ordering is requested."""
        converter = ArrowDataConverter()
        schema = pa.schema(
            [
                pa.field("payload", pa.string()),
                pa.field("id", pa.int64()),
            ]
        )

        result = converter.convert_records_to_arrow_with_schema(
            [{"id": 1, "payload": {"name": "a"}}],
            schema,
        )

        assert result.column_names == ["payload", "id"]

    def test_convert_records_with_schema_applies_canonical_order_when_requested(
        self,
    ) -> None:
        """Schema-aware conversion should support Silver-style canonical ordering."""
        from bioetl.domain.schemas.column_order import canonical_column_order

        converter = ArrowDataConverter()
        schema = pa.schema(
            [
                pa.field("name", pa.string()),
                pa.field("_run_id", pa.string()),
                pa.field("id", pa.int64()),
            ]
        )

        result = converter.convert_records_to_arrow_with_schema(
            [{"id": 1, "name": "Alice", "_run_id": "run-1"}],
            schema,
            apply_column_order=True,
        )

        assert result.column_names == canonical_column_order(["name", "_run_id", "id"])

    def test_convert_records_with_schema_applies_explicit_column_order(self) -> None:
        """Schema-aware conversion should honor explicit column ordering."""
        converter = ArrowDataConverter()
        schema = pa.schema(
            [
                pa.field("id", pa.int64()),
                pa.field("name", pa.string()),
                pa.field("_run_id", pa.string()),
            ]
        )

        result = converter.convert_records_to_arrow_with_schema(
            [{"id": 1, "name": "Alice", "_run_id": "run-1"}],
            schema,
            column_order=["name", "id"],
        )

        assert result.column_names == ["name", "id", "_run_id"]

    def test_convert_records_with_schema_logs_warning_when_keys_missing(self) -> None:
        """Schema-aware conversion should preserve missing-key warning behavior."""
        logger = MagicMock()
        converter = ArrowDataConverter(logger=logger)
        schema = pa.schema([pa.field("id", pa.int64())])

        result = converter.convert_records_to_arrow_with_schema(
            [{"id": 2}, {"id": 1}],
            schema,
            primary_keys=["missing"],
        )

        assert result.column("id").to_pylist() == [2, 1]
        logger.warning.assert_called_once()

    def test_convert_records_with_schema_handles_empty_records(self) -> None:
        """Schema-aware conversion should return an empty table with the requested schema."""
        converter = ArrowDataConverter()
        schema = pa.schema(
            [
                pa.field("id", pa.int64()),
                pa.field("payload", pa.string()),
            ]
        )

        result = converter.convert_records_to_arrow_with_schema([], schema)

        assert result.schema == schema
        assert result.num_rows == 0


class TestArrowSchemaPreparationHelpers:
    """Tests for reusable schema-aware Arrow preparation helpers."""

    def test_get_string_fields_supports_string_and_large_string(self) -> None:
        """String helper should include both string and large_string fields."""
        schema = pa.schema(
            [
                pa.field("id", pa.string()),
                pa.field("payload", pa.large_string()),
                pa.field("count", pa.int64()),
            ]
        )

        assert get_string_fields(schema) == {"id", "payload"}

    def test_build_arrow_schema_preparation_context_tracks_schema_names(self) -> None:
        """Preparation context should preserve schema names and lookup sets."""
        schema = pa.schema(
            [
                pa.field("id", pa.string()),
                pa.field("count", pa.int64()),
            ]
        )

        context = build_arrow_schema_preparation_context(schema)

        assert context.schema_names == ("id", "count")
        assert context.schema_fields == frozenset({"id", "count"})
        assert context.string_fields == frozenset({"id"})

    def test_filter_record_for_schema_serializes_string_backed_complex_values(
        self,
    ) -> None:
        """Schema filter should serialize complex values only for string-backed fields."""
        schema = pa.schema(
            [
                pa.field("id", pa.string()),
                pa.field("payload", pa.string()),
            ]
        )
        context = build_arrow_schema_preparation_context(schema)

        result = filter_record_for_schema(
            {
                "id": "1",
                "payload": {"b": 2, "a": 1},
                "ignored": "drop-me",
            },
            context,
        )

        assert result == {"id": "1", "payload": '{"a":1,"b":2}'}

    def test_serialize_value_for_arrow_schema_keeps_non_string_complex_values(
        self,
    ) -> None:
        """Complex values should only serialize when the schema field is string-like."""
        value = {"a": 1}

        assert (
            serialize_value_for_arrow_schema(value, is_string_field=True) == '{"a":1}'
        )
        assert serialize_value_for_arrow_schema(value, is_string_field=False) == value

    def test_sort_arrow_table_by_primary_keys_returns_sorted_table(self) -> None:
        """Primary-key sort helper should order rows deterministically."""
        table = pa.table({"id": ["c", "a", "b"], "value": [3, 1, 2]})

        result = sort_arrow_table_by_primary_keys(table, ["id"])

        assert result.column("id").to_pylist() == ["a", "b", "c"]

    def test_sort_arrow_table_by_primary_keys_skips_single_row(self) -> None:
        """Single-row tables should bypass sort work."""
        table = pa.table({"id": ["a"], "value": [1]})

        result = sort_arrow_table_by_primary_keys(table, ["id"])

        assert result is table


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
