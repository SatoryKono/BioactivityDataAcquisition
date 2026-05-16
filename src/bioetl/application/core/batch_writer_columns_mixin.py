# mypy: disable-error-code=attr-defined
"""Column-order and schema helpers for BatchWriter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bioetl.domain.types import GoldRecord

_SCHEMA_EXTRACTION_ERRORS = (
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
)


class BatchWriterColumnsMixin:
    """Column resolution helpers extracted from BatchWriter."""

    def _get_schema_columns(
        self,
        schema: Any,  # Any: schema backend object type depends on runtime writer implementation
    ) -> set[str] | None:
        """Extract column names from Pandera schema-like objects."""
        if hasattr(schema, "to_schema"):
            try:
                converted = schema.to_schema()
                return set(converted.columns.keys())
            except _SCHEMA_EXTRACTION_ERRORS:
                pass  # Why: schema hint unavailable, use default column order

        if hasattr(schema, "columns"):
            return set(schema.columns.keys())
        return None

    def _collect_record_columns(self, records: list[GoldRecord]) -> list[str]:
        """Collect columns in stable first-seen order."""
        import itertools

        return list(dict.fromkeys(itertools.chain.from_iterable(records)))

    def _get_column_order(self, columns: Sequence[str]) -> list[str] | None:
        """Resolve explicit column order from configured column groups."""
        if not self._column_orderer:
            return None
        ordered = self._column_orderer.order_column_names(columns)
        return self._apply_system_prefix_order(ordered)

    def _apply_renames_to_records(
        self, records: list[GoldRecord], rename_map: dict[str, str]
    ) -> list[GoldRecord]:
        """Apply column renames to record dictionaries."""
        if not rename_map:
            return records

        renamed_records = []
        for record in records:
            renamed = {}
            for key, value in record.items():
                renamed[rename_map.get(key, key)] = value
            renamed_records.append(renamed)
        return renamed_records

    def _resolve_layer_columns(
        self, layer: Literal["silver", "gold"], available_columns: Sequence[str]
    ) -> tuple[list[str] | None, dict[str, str]]:
        """Resolve column ordering and renames for the requested layer."""
        if not self._data_schema:
            return self._get_column_order(available_columns), {}

        layer_config = getattr(self._data_schema, layer, None)
        if not layer_config:
            return self._get_column_order(available_columns), {}

        if not self._column_orderer:
            if layer_config.columns:
                return (
                    [c for c in layer_config.columns if c in available_columns],
                    layer_config.rename_fields,
                )
            return None, layer_config.rename_fields

        ordered_columns = self._column_orderer.filter_by_layer_config(
            available_columns, layer_config
        )
        ordered_columns = self._apply_system_prefix_order(ordered_columns)
        return ordered_columns, layer_config.rename_fields

    def _apply_system_prefix_order(self, columns: list[str]) -> list[str]:
        """Ensure system fields are first and DQ fields are last."""
        from bioetl.domain.schemas.column_order import (
            DQ_FIELDS_SUFFIX,
            LOOKUP_FIELDS_PREFIX,
            SYSTEM_FIELDS_PREFIX,
        )

        if not columns:
            return columns

        column_set = set(columns)
        prefix = [c for c in SYSTEM_FIELDS_PREFIX if c in column_set]
        lookup = [c for c in LOOKUP_FIELDS_PREFIX if c in column_set]
        suffix = [c for c in DQ_FIELDS_SUFFIX if c in column_set]
        assigned = {*prefix, *lookup, *suffix}
        middle = [c for c in columns if c not in assigned]
        return prefix + lookup + middle + suffix
