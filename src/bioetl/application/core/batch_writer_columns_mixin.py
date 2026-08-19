# mypy: disable-error-code=attr-defined
"""Column-order and schema helpers for BatchWriter."""

from __future__ import annotations

import itertools
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Literal, cast

if TYPE_CHECKING:
    from bioetl.domain.types import GoldRecord

_SCHEMA_EXTRACTION_ERRORS = (
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
)


class BatchWriterColumnsMixin:
    """Column resolution helpers extracted from BatchWriter."""

    _column_orderer: Any = cast(Any, None)  # Any: optional column-order service
    _data_schema: Any = cast(Any, None)  # Any: heterogeneous schema adapter

    def _project_via_to_schema(
        self,
        schema: object,
        column_order: Sequence[str],
    ) -> object | None:
        """Project a schema object through its conversion surface when available."""
        to_schema = getattr(schema, "to_schema", None)
        if not callable(to_schema):
            return None
        try:
            converted = to_schema()
            select_columns = getattr(converted, "select_columns", None)
            if callable(select_columns):
                return cast(object, select_columns(list(column_order)))
        except _SCHEMA_EXTRACTION_ERRORS:
            return None
        return None

    def _project_via_select_columns(
        self,
        schema: object,
        column_order: Sequence[str],
    ) -> object | None:
        """Project a schema object through a direct select_columns surface."""
        select_columns = getattr(schema, "select_columns", None)
        if not callable(select_columns):
            return None
        try:
            return cast(object, select_columns(list(column_order)))
        except _SCHEMA_EXTRACTION_ERRORS:
            return None

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
            names = getattr(schema, "names", ())
            field_fn = getattr(schema, "field", None)
            if not callable(field_fn):
                return None
            projected_fields = [
                field_fn(name) for name in column_order if name in names
            ]
            return cast(
                object,
                pa.schema(projected_fields, metadata=getattr(schema, "metadata", None)),
            )
        except (ImportError, AttributeError, TypeError, ValueError):
            return None

    def _get_schema_columns(
        self,
        schema: object,
    ) -> set[str] | None:
        """Extract column names from Pandera schema-like objects."""
        to_schema = getattr(schema, "to_schema", None)
        if callable(to_schema):
            try:
                converted = to_schema()
                columns = getattr(converted, "columns", None)
                if isinstance(columns, dict):
                    return set(columns.keys())
            except _SCHEMA_EXTRACTION_ERRORS:
                pass  # Why: schema hint unavailable, use default column order
        columns = getattr(schema, "columns", None)
        if isinstance(columns, dict):
            return set(columns.keys())
        return None

    def _collect_record_columns(self, records: list[GoldRecord]) -> list[str]:
        """Collect columns in stable first-seen order."""
        return list(dict.fromkeys(itertools.chain.from_iterable(records)))

    def _get_column_order(self, columns: Sequence[str]) -> list[str] | None:
        """Resolve explicit column order from configured column groups."""
        if not self._column_orderer:
            return None
        ordered = self._column_orderer.order_column_names(columns)
        return self._apply_system_prefix_order(ordered)

    def _apply_renames_to_column_order(
        self,
        column_order: Sequence[str] | None,
        rename_map: dict[str, str],
    ) -> list[str] | None:
        """Map a column-order list through rename_map, preserving order."""
        if column_order is None or not rename_map:
            return list(column_order) if column_order is not None else None
        return [rename_map.get(name, name) for name in column_order]

    def _apply_renames_to_schema(
        self,
        schema: object,
        rename_map: dict[str, str],
    ) -> object:
        """Rename schema field names when the adapter exposes rename_columns."""
        if schema is None or not rename_map:
            return schema
        names = getattr(schema, "names", None)
        rename_columns = getattr(schema, "rename_columns", None)
        if names is None or not callable(rename_columns):
            return schema
        try:
            name_list = list(names)
            dest_names = [rename_map.get(name, name) for name in name_list]
            if dest_names == name_list:
                return schema
            return cast(object, rename_columns(dest_names))
        except _SCHEMA_EXTRACTION_ERRORS:
            return schema

    def _apply_layer_renames(
        self,
        records: list[GoldRecord],
        column_order: Sequence[str] | None,
        schema: object,
        rename_map: dict[str, str],
    ) -> tuple[list[GoldRecord], list[str] | None, object]:
        """Apply rename_map to records, column order, and schema consistently."""
        if not rename_map:
            return (
                records,
                list(column_order) if column_order is not None else None,
                schema,
            )
        return (
            self._apply_renames_to_records(records, rename_map),
            self._apply_renames_to_column_order(column_order, rename_map),
            self._apply_renames_to_schema(schema, rename_map),
        )

    def _apply_renames_to_records(
        self, records: list[GoldRecord], rename_map: dict[str, str]
    ) -> list[GoldRecord]:
        """Apply column renames to record dictionaries.

        Rejects a record when two source keys, or a source key and an existing
        destination column, resolve to the same destination name.
        """
        if not rename_map:
            return records
        renamed_records = []
        for record in records:
            renamed: dict[str, object] = {}
            for key, value in record.items():
                dest = rename_map.get(key, key)
                if dest in renamed:
                    raise ValueError(
                        f"Column rename collision: {key!r} and an existing field "
                        f"both resolve to {dest!r}"
                    )
                renamed[dest] = value
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
