"""Merged storage port for composite pipeline operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from bioetl.domain.types import BronzeRecord, GoldRecord

if TYPE_CHECKING:
    from datetime import datetime

    from pandera.api.dataframe.container import DataFrameSchema

__all__ = ["MergedStoragePort"]


@runtime_checkable
class MergedStoragePort(Protocol):
    """Port for composite pipeline merged writes.

    Used by composite pipelines where schema is dynamically determined
    by the merge operation, bypassing strict schema validation.
    """

    async def write_silver_merged(
        self,
        table_name: str,
        records: list[BronzeRecord],  # BronzeRecord: merged Silver records
        primary_keys: list[str] | None = None,
        *,
        completed_at: datetime | None = None,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        preserve_column_order: bool = False,
    ) -> None:
        """Write merged records to Silver layer without explicit schema.

        Used by composite pipelines where schema is dynamically determined
        by the merge operation. Schema is inferred from the records.

        Args:
            table_name: The name of the table to write to.
            records: A list of dictionaries representing merged records.
            primary_keys: Optional list of column names for sorting.
            completed_at: Optional deterministic metadata timestamp for merged sidecars.
            run_id: Optional composite run ID for metadata tracking.
            sources_used: Optional list of source pipelines used in merge.
            preserve_column_order: If True, skip canonical_column_order()
                and preserve the column order from records (e.g. semantic
                ordering applied by ColumnOrderService in composite pipelines).
        """
        ...

    async def write_gold_merged(
        self,
        table_name: str,
        records: list[GoldRecord],
        primary_keys: list[str] | None = None,
        *,
        completed_at: datetime | None = None,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        preserve_column_order: bool = False,
        schema: DataFrameSchema[Any] | None = None,  # Any: composite schema generic stays backend-defined
    ) -> None:
        """Write merged records to Gold layer without Pandera schema.

        Used by composite pipelines where schema is dynamically determined
        by the merge operation. Optional Pandera validation can be applied
        when a composite contract is available.

        Args:
            table_name: The name of the table to write to.
            records: A list of dictionaries representing merged records.
            primary_keys: Optional list of column names for sorting.
            completed_at: Optional deterministic metadata timestamp for merged sidecars.
            run_id: Optional composite run ID for metadata tracking.
            sources_used: Optional list of source pipelines used in merge.
            preserve_column_order: If True, skip canonical_column_order()
                and preserve the column order from records (e.g. semantic
                ordering applied by ColumnOrderService in composite pipelines).
            schema: Optional Pandera schema used for strict contract validation.
        """
        ...
