"""Arrow preparation helpers for SilverWriter."""

from __future__ import annotations

__all__ = ["SilverWriterArrowMixin"]


from typing import TYPE_CHECKING

import orjson
import pyarrow as pa

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


class SilverWriterArrowMixin:
    """Mixin with Arrow-table preparation logic."""

    def _prepare_arrow_data(
        self,
        records: list[BronzeRecord],
        schema: pa.Schema,
        primary_keys: list[str],
        column_order: list[str] | None = None,
    ) -> pa.Table:
        """Prepare Arrow table from records with schema filtering and sorting."""
        schema_names = schema.names
        string_fields = self._collect_string_fields(schema)
        filtered_records = [
            self._filter_record(record, schema_names, string_fields)
            for record in records
        ]
        arrow_data = pa.Table.from_pylist(filtered_records, schema=schema)
        arrow_data = self._order_columns(arrow_data, column_order)

        if primary_keys:
            arrow_data = arrow_data.sort_by(
                [(key, "ascending") for key in primary_keys]
            )

        return arrow_data

    @staticmethod
    def _collect_string_fields(schema: pa.Schema) -> set[str]:
        return {
            field.name
            for field in schema
            if pa.types.is_string(field.type) or pa.types.is_large_string(field.type)
        }

    @staticmethod
    def _filter_record(
        record: BronzeRecord,
        schema_names: list[str],
        string_fields: set[str],
    ) -> BronzeRecord:
        filtered_record: BronzeRecord = {}
        for key in schema_names:
            if key not in record:
                continue
            value = record[key]
            if (
                value is not None
                and key in string_fields
                and isinstance(value, (dict, list))
            ):
                value = orjson.dumps(value, option=orjson.OPT_SORT_KEYS).decode("utf-8")
            filtered_record[key] = value
        return filtered_record

    @staticmethod
    def _order_columns(
        arrow_data: pa.Table,
        column_order: list[str] | None,
    ) -> pa.Table:
        if column_order:
            ordered_columns = [
                column for column in column_order if column in arrow_data.column_names
            ]
            remaining = [
                column
                for column in arrow_data.column_names
                if column not in ordered_columns
            ]
            return arrow_data.select(ordered_columns + remaining)
        from bioetl.domain.schemas.column_order import canonical_column_order

        ordered_columns = canonical_column_order(list(arrow_data.column_names))
        return arrow_data.select(ordered_columns)
