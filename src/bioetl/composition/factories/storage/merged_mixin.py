"""Merged write and read operations mixin for StorageAdapter."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Literal, Protocol, cast

from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.infrastructure.storage.gold_writer import GoldWriter
    from bioetl.infrastructure.storage.silver_writer import SilverWriter

__all__ = ["StorageAdapterMergedMixin"]


class _SilverMergedWriteProtocol(Protocol):
    """Minimal bound-method contract for merged Silver writes."""

    async def write_silver_merged(
        self,
        table_name: str,
        records: list[JsonDict],
        primary_keys: list[str] | None = None,
        *,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        preserve_column_order: bool = False,
    ) -> None: ...


class StorageAdapterMergedMixin:
    """Mixin providing merged write and read operations for composite pipelines."""

    silver: SilverWriter
    gold: GoldWriter
    _COMPOSITE_GOLD_SCHEMAS: ClassVar[
        JsonDict  # Any: record/metadata values are heterogeneous
    ]

    def get_table_path(
        self,
        table_name: str,
        layer: Literal["silver", "gold"] = "silver",
    ) -> Path:
        """Resolve the full path to a Delta table.

        Delegates to the underlying writer implementation.

        Args:
            table_name: Database table name.
            layer: Storage layer path resolver (``"silver"`` or ``"gold"``).

        Returns:
            Table path.
        """
        if layer == "gold":
            return self.gold.get_table_path(table_name)
        return self.silver.get_table_path(table_name)

    async def read_silver(
        self,
        table_name: str,
        columns: list[str] | None = None,
    ) -> list[
        JsonDict  # Any: record/metadata values are heterogeneous
    ]:
        """Read records from a Silver layer Delta table.

        Args:
            table_name: The name of the table to read (e.g., 'chembl/activity').
            columns: Optional list of columns to select. If None, reads all columns.

        Returns:
            List of dictionaries, where each dictionary represents a record.

        Raises:
            FileNotFoundError: If the table does not exist.
        """
        return list(await self.silver.read_silver(table_name, columns=columns))

    async def write_silver_merged(
        self,
        table_name: str,
        records: list[
            JsonDict  # Any: record/metadata values are heterogeneous
        ],
        primary_keys: list[str] | None = None,
        *,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        preserve_column_order: bool = False,
    ) -> None:
        """Write merged records to Silver layer without explicit schema.

        Used by composite pipelines where schema is dynamically determined.

        Args:
            table_name: The name of the table to write to.
            records: A list of dictionaries representing merged records.
            primary_keys: Optional list of column names for sorting.
            run_id: Optional composite run ID for metadata tracking.
            sources_used: Optional list of source pipelines used in merge.
            preserve_column_order: If True, skip canonical reordering.
        """
        await cast(
            _SilverMergedWriteProtocol,
            self.silver,
        ).write_silver_merged(
            table_name,
            records,
            primary_keys,
            run_id=run_id,
            sources_used=sources_used,
            preserve_column_order=preserve_column_order,
        )

    async def write_gold_merged(
        self,
        table_name: str,
        records: list[
            JsonDict  # Any: record/metadata values are heterogeneous
        ],
        primary_keys: list[str] | None = None,
        *,
        completed_at: object | None = None,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        preserve_column_order: bool = False,
        schema: object | None = None,
    ) -> None:
        """Write merged records to Gold layer without Pandera schema.

        Used by composite pipelines where schema is dynamically determined.

        Args:
            table_name: The name of the table to write to.
            records: A list of dictionaries representing merged records.
            primary_keys: Optional list of column names for sorting.
            completed_at: Optional deterministic metadata timestamp for merged sidecars.
            run_id: Optional composite run ID for metadata tracking.
            sources_used: Optional list of source pipelines used in merge.
            preserve_column_order: If True, skip canonical reordering.
            schema: Optional Pandera schema for strict contract validation.
        """
        composite_schema = self._COMPOSITE_GOLD_SCHEMAS.get(table_name)

        await self.gold.write_gold_merged(
            table_name,
            records,
            primary_keys,
            schema=composite_schema,
            completed_at=completed_at,
            run_id=run_id,
            sources_used=sources_used,
            preserve_column_order=preserve_column_order,
        )
