"""Arrow table conversion utilities for Delta Lake writers.

Extracts Arrow table preparation logic from GoldWriter to reduce
file size and improve reusability.

Implements RULES.md §2.4 and ADR-014 for deterministic writes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pyarrow as pa

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


class ArrowDataConverter:
    """Converter for preparing PyArrow tables for Delta Lake writes.

    Handles:
    - Null type coercion (Delta Lake doesn't support null type)
    - Canonical column ordering (ADR-014)
    - Primary key sorting for deterministic writes

    This class extracts the Arrow table preparation logic from GoldWriter
    to reduce file size and improve testability.
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
            new_fields = [
                pa.field(f.name, self.sanitize_type_for_delta(f.type), f.nullable)
                for f in dtype
            ]
            return pa.struct(new_fields)
        elif pa.types.is_map(dtype):
            key_type = self.sanitize_type_for_delta(dtype.key_type)
            item_type = self.sanitize_type_for_delta(dtype.item_type)
            return pa.map_(key_type, item_type)
        return dtype

    def convert_records_to_arrow(
        self,
        records: list[dict[str, Any]],
        primary_keys: list[str] | None = None,
        column_order: list[str] | None = None,
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

        Returns:
            PyArrow Table ready for Delta Lake write.
        """
        arrow_data = pa.Table.from_pylist(records)

        arrow_data = self._apply_column_ordering(arrow_data, column_order)

        # Check if schema needs sanitization (contains null types)
        schema_str = str(arrow_data.schema).lower()
        if "null" in schema_str:
            arrow_data = self._sanitize_null_columns(arrow_data)

        arrow_data = self._apply_sorting(arrow_data, primary_keys)

        return arrow_data

    def _apply_column_ordering(
        self,
        arrow_data: pa.Table,
        column_order: list[str] | None,
    ) -> pa.Table:
        """Apply canonical or explicit column ordering."""
        from bioetl.domain.schemas.column_order import canonical_column_order

        if column_order:
            ordered_columns = [c for c in column_order if c in arrow_data.column_names]
            remaining = [c for c in arrow_data.column_names if c not in ordered_columns]
            return arrow_data.select(ordered_columns + remaining)

        ordered_columns = canonical_column_order(list(arrow_data.column_names))
        return arrow_data.select(ordered_columns)

    def _apply_sorting(
        self,
        arrow_data: pa.Table,
        primary_keys: list[str] | None,
    ) -> pa.Table:
        """Sort table by primary keys for deterministic writes."""
        if primary_keys:
            valid_keys = [pk for pk in primary_keys if pk in arrow_data.schema.names]
            if valid_keys:
                return arrow_data.sort_by([(pk, "ascending") for pk in valid_keys])
        return arrow_data

    def _convert_column_to_string(self, col: pa.Array) -> pa.Array:
        """Convert column to string type handling nulls safely."""
        return pa.array(
            [str(v) if v is not None else None for v in col.to_pylist()],
            type=pa.string(),
        )

    def _process_column_for_delta(
        self, col: pa.Array, field: pa.Field
    ) -> tuple[pa.Array, pa.Field]:
        """Process a single column for Delta Lake compatibility."""
        new_type = self.sanitize_type_for_delta(field.type)

        if pa.types.is_null(field.type):
            new_col = pa.array([None] * len(col), type=pa.string())
            return new_col, pa.field(field.name, pa.string(), field.nullable)

        if new_type == field.type:
            return col, field

        try:
            new_col = col.cast(new_type)
        except pa.ArrowInvalid:
            new_col = self._convert_column_to_string(col)

        return new_col, pa.field(field.name, new_type, field.nullable)

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
            new_col, new_field = self._process_column_for_delta(col, field)
            new_columns.append(new_col)
            new_fields.append(new_field)

        new_schema = pa.schema(new_fields)
        return pa.Table.from_arrays(new_columns, schema=new_schema)


__all__ = ["ArrowDataConverter"]
