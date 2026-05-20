# mypy: disable-error-code=attr-defined
"""Column-order and schema helpers for BatchWriter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

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

    def _project_via_to_schema(
        self,
        schema: object,
        column_order: Sequence[str],
    ) -> object | None:
        """Project a schema object through its conversion surface when available."""
        if not hasattr(schema, "to_schema"):
            return None
        try:
            converted = schema.to_schema()
            if hasattr(converted, "select_columns"):
                return converted.select_columns(list(column_order))
        except _SCHEMA_EXTRACTION_ERRORS:
            return schema
        return None

    def _project_via_select_columns(
        self,
        schema: object,
        column_order: Sequence[str],
    ) -> object | None:
        """Project a schema object through a direct select_columns surface."""
        if not hasattr(schema, "select_columns"):
            return None
        try:
            return schema.select_columns(list(column_order))
        except _SCHEMA_EXTRACTION_ERRORS:
            return schema

    def _project_pyarrow_schema(
        self,
        schema: object,
        column_order: Sequence[str],
    ) -> object | None:
        """Project a PyArrow schema while preserving metadata when available."""
        try:
            import pyarrow as pa

            if not isinstance(schema, pa.Schema):
                return None
            projected_fields = [
                schema.field(name) for name in column_order if name in schema.names
            ]
            return pa.schema(projected_fields, metadata=schema.metadata)
        except (ImportError, AttributeError, TypeError, ValueError):
            return schema

    def _get_schema_columns(
        self,
        schema: object,
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
        columns: list[str] = []
        seen: set[str] = set()
        for record in records:
            for key in record:
                if key not in seen:
                    seen.add(key)
                    columns.append(key)
        return columns

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

    def _project_schema_for_layer(
        self,
        layer: Literal["silver", "gold"],
        schema: object,
        column_order: Sequence[str] | None,
    ) -> object:
        """Project a writer schema to the layer's configured output columns."""
        if schema is None or not column_order or not self._data_schema:
            return schema

        layer_config = getattr(self._data_schema, layer, None)
        if layer_config is None:
            return schema

        projected = self._project_via_to_schema(schema, column_order)
        if projected is not None:
            return projected
        projected = self._project_via_select_columns(schema, column_order)
        if projected is not None:
            return projected
        projected = self._project_pyarrow_schema(schema, column_order)
        if projected is not None:
            return projected
        return schema

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
