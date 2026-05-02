"""Merged write and read operations mixin for StorageBundle."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Literal, Protocol, cast

from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from pandera.polars import DataFrameSchema

    from bioetl.infrastructure.storage.gold_writer import GoldWriter
    from bioetl.infrastructure.storage.silver_writer import SilverWriter

__all__ = ["StorageBundleMergedMixin"]


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


class _GoldMergedWriteProtocol(Protocol):
    """Minimal bound-method contract for merged Gold writes."""

    async def write_gold_merged(
        self,
        table_name: str,
        records: list[JsonDict],
        primary_keys: list[str] | None = None,
        *,
        schema: DataFrameSchema,
        completed_at: datetime | None = None,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        preserve_column_order: bool = False,
    ) -> None: ...


class StorageBundleMergedMixin:
    """Mixin providing merged write and read operations for composite pipelines."""

    silver: SilverWriter
    gold: GoldWriter
    _COMPOSITE_GOLD_SCHEMAS: ClassVar[dict[str, object]]

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
        completed_at: datetime | None = None,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        preserve_column_order: bool = False,
        schema: object | None = None,
    ) -> None:
        """Write merged records to Gold layer with a required composite schema.

        Used by composite pipelines where the schema is resolved from the
        registered composite Gold contract surface.

        Args:
            table_name: The name of the table to write to.
            records: A list of dictionaries representing merged records.
            primary_keys: Optional list of column names for sorting.
            completed_at: Optional deterministic metadata timestamp for merged sidecars.
            run_id: Optional composite run ID for metadata tracking.
            sources_used: Optional list of source pipelines used in merge.
            preserve_column_order: If True, skip canonical reordering.
            schema: Optional caller-provided Pandera schema. If omitted, a
                registered composite schema must exist for ``table_name``.
        """
        composite_schema = schema or self._COMPOSITE_GOLD_SCHEMAS.get(table_name)
        if composite_schema is None:
            raise ValueError(
                "Composite Gold write requires a registered strict schema: "
                f"table_name={table_name}"
            )

        await cast(
            _GoldMergedWriteProtocol,
            self.gold,
        ).write_gold_merged(
            table_name,
            records,
            primary_keys,
            schema=composite_schema,
            completed_at=completed_at,
            run_id=run_id,
            sources_used=sources_used,
            preserve_column_order=preserve_column_order,
        )
