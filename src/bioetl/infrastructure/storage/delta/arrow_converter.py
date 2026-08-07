"""Arrow table conversion utilities for Delta Lake writers.

Extracts shared Arrow table preparation logic from storage writers to reduce
file size and keep schema-aware conversion behavior centralized.

Implements RULES.md §2.4 and ADR-014 for deterministic writes.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

import orjson
import pyarrow as pa

from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


@dataclass(frozen=True, slots=True)
class ArrowSchemaPreparationContext:
    """Prepared schema context for deterministic schema-aware Arrow conversion."""

    schema_names: tuple[str, ...]
    schema_fields: frozenset[str]
    string_fields: frozenset[str]


def serialize_value_for_arrow_schema(
    value: Any,  # Any: Arrow field value type varies by input record
    is_string_field: bool,
) -> Any:  # Any: schema-aware conversion preserves heterogeneous scalar types
    """Serialize one value for schema-aware Arrow conversion."""
    if value is None:
        return None
    if is_string_field and isinstance(value, (dict, list)):
        return orjson.dumps(value, option=orjson.OPT_SORT_KEYS).decode("utf-8")
    return value


def get_string_fields(schema: pa.Schema) -> set[str]:
    """Return field names backed by string-like Arrow types."""
    return {
        field.name
        for field in schema
        if pa.types.is_string(field.type) or pa.types.is_large_string(field.type)
    }


def build_arrow_schema_preparation_context(
    schema: pa.Schema,
) -> ArrowSchemaPreparationContext:
    """Build immutable schema context for filtered Arrow conversion."""
    schema_names = tuple(schema.names)
    return ArrowSchemaPreparationContext(
        schema_names=schema_names,
        schema_fields=frozenset(schema_names),
        string_fields=frozenset(get_string_fields(schema)),
    )


def filter_record_for_schema(
    record: JsonDict,
    context: ArrowSchemaPreparationContext,
) -> JsonDict:
    """Filter one record to schema fields and serialize string-backed complex values."""
    filtered: JsonDict = {}
    string_fields = context.string_fields
    for key in context.schema_names:
        if key not in record:
            continue
        value = record[key]
        filtered[key] = serialize_value_for_arrow_schema(
            value,
            key in string_fields,
        )
    return filtered


def sort_arrow_table_by_primary_keys(
    arrow_data: pa.Table,
    primary_keys: list[str] | None,
    *,
    schema_names: Sequence[str] | None = None,
    logger: LoggerPort | None = None,
) -> pa.Table:
    """Sort an Arrow table by available primary keys for deterministic writes."""
    if not primary_keys or arrow_data.num_rows < 2:
        return arrow_data

    available_schema_names = tuple(schema_names or arrow_data.schema.names)
    valid_keys = [pk for pk in primary_keys if pk in available_schema_names]
    if valid_keys:
        return arrow_data.sort_by([(pk, "ascending") for pk in valid_keys])

    if logger is not None:
        logger.warning(
            "Primary keys not found in schema, skipping sort",
            primary_keys=primary_keys,
            schema_fields=available_schema_names,
        )
    return arrow_data


class ArrowDataConverter:
    """Converter for preparing PyArrow tables for Delta Lake writes.

    Handles:
    - Schema-aware record filtering and serialization
    - Null type coercion (Delta Lake doesn't support null type)
    - Canonical column ordering (ADR-014)
    - Primary key sorting for deterministic writes

    This class centralizes shared Arrow preparation logic used by storage
    writers to reduce duplication and improve testability.
    """

    def __init__(self, logger: LoggerPort | None = None) -> None:
        """Initialize Arrow converter.

        Args:
            logger: Optional logger for diagnostics.
        """
        self._logger = logger

    def sanitize_type_for_delta(self, dtype: pa.DataType) -> pa.DataType:
        """Recursively replace null types with string for Delta Lake compatibility.

        Delta Lake doesn't support null type in any form. This method converts:
        - null -> string
        - list<null> -> list<string>
        - struct with null fields -> struct with string fields
        - map with null key/value types -> map with string types

        Args:
            dtype: PyArrow DataType to sanitize.

        Returns:
            Sanitized DataType with null replaced by string.
        """
        if pa.types.is_null(dtype):
            return pa.string()
        elif pa.types.is_list(dtype):
            inner = self.sanitize_type_for_delta(dtype.value_type)
            return pa.list_(inner)
        elif pa.types.is_large_list(dtype):
            inner = self.sanitize_type_for_delta(dtype.value_type)
            return pa.large_list(inner)
        elif pa.types.is_struct(dtype):
            # StructType is iterable at runtime; local pyarrow stubs type DataType
            # without __iter__, so cast through Any for static checkers.
            struct_fields = cast(
                Sequence[pa.Field],
                cast(Any, dtype),  # Any: pyarrow StructType lacks __iter__ in stubs
            )
            new_fields = [
                pa.field(f.name, self.sanitize_type_for_delta(f.type), f.nullable)
                for f in struct_fields
            ]
            return pa.struct(new_fields)
        elif pa.types.is_map(dtype):
            key_type = self.sanitize_type_for_delta(dtype.key_type)
            item_type = self.sanitize_type_for_delta(dtype.item_type)
            return pa.map_(key_type, item_type)
        return dtype

    def _apply_column_order(
        self,
        arrow_data: pa.Table,
        column_order: list[str] | None,
    ) -> pa.Table:
        """Apply explicit or canonical column order to an Arrow table.

        Returns:
            Arrow table with columns reordered per explicit or canonical order.
        """
        from bioetl.domain.schemas.column_order import canonical_column_order

        if column_order:
            ordered = [c for c in column_order if c in arrow_data.column_names]
            remaining = [c for c in arrow_data.column_names if c not in ordered]
            return arrow_data.select(ordered + remaining)

        ordered = canonical_column_order(list(arrow_data.column_names))
        return arrow_data.select(ordered)

    def _sort_by_keys(
        self,
        arrow_data: pa.Table,
        primary_keys: list[str] | None,
    ) -> pa.Table:
        """Sort Arrow table by primary keys for deterministic writes.

        Returns:
            Arrow table sorted ascending by the provided primary keys, unsorted if none provided.
        """
        return sort_arrow_table_by_primary_keys(
            arrow_data,
            primary_keys,
            logger=self._logger,
        )

    def convert_records_to_arrow(
        self,
        records: list[JsonDict],  # Any: record/metadata values are heterogeneous
        primary_keys: list[str] | None = None,
        column_order: list[str] | None = None,
        apply_column_order: bool = True,
    ) -> pa.Table:
        """Convert records to PyArrow table with null type handling.

        Performs:
        1. Convert records to Arrow table
        2. Apply canonical column order (ADR-014) or an explicit order
        3. Coerce null types to string (Delta Lake compatibility)
        4. Sort by primary keys for deterministic writes

        Args:
            records: List of record dictionaries.
            primary_keys: Optional list of columns for sorting.
            column_order: Optional explicit column order to apply.
            apply_column_order: If False, preserve the original Arrow column order.

        Returns:
            PyArrow Table ready for Delta Lake write.
        """
        if not records:
            return pa.table({})

        arrow_data = pa.Table.from_pylist(records)
        if column_order is not None or apply_column_order:
            arrow_data = self._apply_column_order(arrow_data, column_order)

        # Check if schema needs sanitization (contains null types)
        if "null" in str(arrow_data.schema).lower():
            arrow_data = self._sanitize_null_columns(arrow_data)

        return self._sort_by_keys(arrow_data, primary_keys)

    def convert_records_to_arrow_with_schema(
        self,
        records: list[JsonDict],  # Any: record/metadata values are heterogeneous
        schema: pa.Schema,
        primary_keys: list[str] | None = None,
        column_order: list[str] | None = None,
        apply_column_order: bool = False,
    ) -> pa.Table:
        """Convert records to Arrow using schema filtering, serialization, and sorting."""
        if not records:
            return pa.Table.from_pylist([], schema=schema)

        try:
            arrow_data = pa.Table.from_pylist(records, schema=schema)
        except (pa.ArrowInvalid, pa.ArrowTypeError, TypeError, ValueError):
            context = build_arrow_schema_preparation_context(schema)
            filtered_records = [
                filter_record_for_schema(record, context) for record in records
            ]
            arrow_data = pa.Table.from_pylist(filtered_records, schema=schema)
        if column_order is not None or apply_column_order:
            arrow_data = self._apply_column_order(arrow_data, column_order)
        return sort_arrow_table_by_primary_keys(
            arrow_data,
            primary_keys,
            schema_names=schema.names,
            logger=self._logger,
        )

    def _sanitize_single_null_column(
        self,
        col: pa.Array | pa.ChunkedArray,
        field_type: pa.DataType,
        new_type: pa.DataType,
    ) -> tuple[pa.Array | pa.ChunkedArray, pa.DataType]:
        """Sanitize one Arrow column; return (column, effective_type)."""
        if pa.types.is_null(field_type):
            return pa.array([None] * len(col), type=pa.string()), pa.string()
        if new_type == field_type:
            return col, new_type
        try:
            return col.cast(new_type), new_type
        except (pa.ArrowInvalid, pa.ArrowNotImplementedError):
            fallback_type = new_type if new_type is not None else pa.string()
            values = [str(v) if v is not None else None for v in col.to_pylist()]
            try:
                return pa.array(values, type=fallback_type), fallback_type
            except (pa.ArrowInvalid, pa.ArrowNotImplementedError, TypeError):
                return pa.array(values, type=pa.string()), pa.string()

    def _sanitize_null_columns(self, arrow_data: pa.Table) -> pa.Table:
        """Sanitize null-typed columns in Arrow table.

        Converts columns with null type to string type while preserving
        the null values. This is necessary because Delta Lake doesn't
        support null type.

        Args:
            arrow_data: Arrow table that may contain null-typed columns.

        Returns:
            Arrow table with null columns converted to string type.
        """
        new_columns = []
        new_fields = []

        for i, field in enumerate(arrow_data.schema):
            col = arrow_data.column(i)
            new_type = self.sanitize_type_for_delta(field.type)
            new_col, effective_type = self._sanitize_single_null_column(
                col, field.type, new_type
            )
            new_columns.append(new_col)
            new_fields.append(pa.field(field.name, effective_type, field.nullable))

        new_schema = pa.schema(new_fields)
        return pa.Table.from_arrays(new_columns, schema=new_schema)


__all__ = [
    "ArrowDataConverter",
    "ArrowSchemaPreparationContext",
    "build_arrow_schema_preparation_context",
    "filter_record_for_schema",
    "get_string_fields",
    "serialize_value_for_arrow_schema",
    "sort_arrow_table_by_primary_keys",
]
