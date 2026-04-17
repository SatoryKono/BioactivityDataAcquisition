"""Arrow operations service for SilverWriter (composition pattern)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pyarrow as pa

from bioetl.infrastructure.storage.silver.support import (
    prepare_arrow_data as _prepare_arrow_data_standalone,
)

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


@dataclass(frozen=True, slots=True)
class SilverArrowOperations:
    """Arrow operations service for Silver layer writes.

    This service encapsulates Arrow table preparation logic previously in SilverWriterArrowMixin,
    following the composition pattern for better separation of concerns and testability.
    """

    def _prepare_arrow_data(
        self,
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
        return _prepare_arrow_data_standalone(
            records=records,
            schema=schema,
            primary_keys=primary_keys,
            column_order=column_order,
        )
