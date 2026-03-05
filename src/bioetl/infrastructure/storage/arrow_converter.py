"""Arrow table conversion utilities for Delta Lake writers.

Extracts Arrow table preparation logic from GoldWriter to reduce
file size and improve reusability.

Implements RULES.md §2.4 and ADR-014 for deterministic writes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pyarrow as pa

from bioetl.domain.types import JsonDict

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

    def _apply_column_order(
        self,
        arrow_data: pa.Table,
        column_order: list[str] | None,
    ) -> pa.Table:
        """Apply explicit or canonical column order to an Arrow table."""
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
        """Sort Arrow table by primary keys for deterministic writes."""
        if not primary_keys:
            return arrow_data
        valid_keys = [pk for pk in primary_keys if pk in arrow_data.schema.names]
        if valid_keys:
            return arrow_data.sort_by([(pk, "ascending") for pk in valid_keys])
        return arrow_data

    def convert_records_to_arrow(
        self,
        records: list[JsonDict],  # Any: record/metadata values are heterogeneous
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
        arrow_data = self._apply_column_order(arrow_data, column_order)

        # Check if schema needs sanitization (contains null types)
        if "null" in str(arrow_data.schema).lower():
            arrow_data = self._sanitize_null_columns(arrow_data)

        return self._sort_by_keys(arrow_data, primary_keys)

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

            if pa.types.is_null(field.type):
                # Create string array with all nulls
                new_col = pa.array([None] * len(col), type=pa.string())
                new_columns.append(new_col)
            elif new_type != field.type:
                # Try to cast for nested types
                try:
                    new_columns.append(col.cast(new_type))
                except pa.ArrowInvalid:
                    # If cast fails, convert to string via Python
                    new_columns.append(
                        pa.array(
                            [
                                str(v) if v is not None else None
                                for v in col.to_pylist()
                            ],
                            type=pa.string(),
                        )
                    )
            else:
                new_columns.append(col)

            new_fields.append(pa.field(field.name, new_type, field.nullable))

        new_schema = pa.schema(new_fields)
        return pa.Table.from_arrays(new_columns, schema=new_schema)


__all__ = ["ArrowDataConverter"]
