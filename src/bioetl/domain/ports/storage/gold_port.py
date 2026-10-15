"""Gold layer storage port."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Protocol, runtime_checkable

from bioetl.domain.types import GoldRecord, RunID, ScdConfig

__all__ = ["GoldStoragePort"]


@runtime_checkable
class GoldStoragePort(Protocol):
    """Port for Gold layer storage operations.

    Covers Gold write (with Pandera validation) and layer clear.
    """

    async def write_gold(
        self,
        table_name: str,
        records: list[GoldRecord],
        schema: Any,  # Any: strict schema payload stays opaque to the domain contract
        primary_keys: list[str] | None = None,
        mode: Literal["overwrite", "append", "scd2"] = "overwrite",
        *,
        scd_config: ScdConfig | None = None,
        column_order: list[str] | None = None,
        ingestion_ts: datetime | None = None,
        run_id: RunID | None = None,
        silver_refs: (
            list[Any] | None  # Any: port contract allows heterogeneous list items
        ) = None,  # Any: port contract allows heterogeneous list items
    ) -> None:
        """Write aggregated or validated records to the Gold layer.

        Args:
            table_name: The name of the table to write to.
            records: A list of dictionaries, where each dictionary is a gold record.
            schema: Opaque strict-schema payload required by the storage implementation.
            primary_keys: Optional list of column names for sorting/deduplication.
            mode: The write mode (e.g., 'overwrite', 'append', 'scd2').
            scd_config: Optional SCD2 configuration.
            column_order: Optional explicit column order to apply.
            ingestion_ts: Ingestion timestamp from application layer
                         (single source of time per ADR-014). Required for audit.
            run_id: Run identifier for audit correlation across layers.
            silver_refs: Optional list of SilverWriteResult from Silver writes.
                If provided, source_tables will be populated in Gold metadata
                for complete lineage tracking (REQ-LINEAGE-002).

        Raises:
            ValueError: If schema validation fails (strict=True required).
        """
        ...

    async def clear_gold(self, table_name: str, dry_run: bool = False) -> int:
        """Clear Gold layer data for a specific table.

        Clears both Delta tables and CSV exports (if configured).
        Should only be called for rebuild/backfill runs, NOT for incremental.

        Args:
            table_name: The name of the table to clear.
            dry_run: If True, only count what would be deleted.

        Returns:
            Count of cleared items (tables + files).
        """
        ...
