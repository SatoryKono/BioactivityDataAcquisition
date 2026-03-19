"""Arrow preparation helpers for SilverWriter."""

from __future__ import annotations

__all__ = ["SilverWriterArrowMixin"]

from typing import TYPE_CHECKING, Protocol

import pyarrow as pa

from bioetl.infrastructure.storage.delta.arrow_converter import ArrowDataConverter

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.types import BronzeRecord


class _SilverWriterArrowContext(Protocol):
    """Structural host contract for shared Silver Arrow preparation."""

    _arrow_converter: ArrowDataConverter
    logger: LoggerPort


class SilverWriterArrowMixin:
    """Mixin with Arrow-table preparation logic."""

    def _prepare_arrow_data(
        self: _SilverWriterArrowContext,
        records: list[BronzeRecord],
        schema: pa.Schema,
        primary_keys: list[str],
        column_order: list[str] | None = None,
    ) -> pa.Table:
        """Prepare Arrow table from records with schema filtering and sorting.

        Args:
            records: List of Bronze record dicts to convert to Arrow format.
            schema: PyArrow schema used to filter and type-cast the records.
            primary_keys: List of column names used for ascending sort order.
            column_order: Optional explicit column ordering; uses canonical order if None.

        Returns:
            PyArrow Table filtered to schema columns, ordered, and sorted by primary keys.
        """
        return self._arrow_converter.convert_records_to_arrow_with_schema(
            records,
            schema,
            primary_keys=primary_keys,
            column_order=column_order,
            apply_column_order=True,
        )
