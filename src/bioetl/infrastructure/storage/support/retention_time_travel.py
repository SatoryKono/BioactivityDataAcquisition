"""Time-travel helper for retention operations."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime

from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.domain.exceptions import TableNotFoundError
from bioetl.infrastructure.storage.support.retention_delta import get_table_path


async def load_time_travel_table(
    *,
    base_path: str,
    table_name: str,
    version: int | None = None,
    timestamp: datetime | None = None,
    delta_table_factory: Callable[..., DeltaTable] = DeltaTable,
) -> DeltaTable:
    """Read a Delta table snapshot at a specific version or timestamp."""
    if version is not None and timestamp is not None:
        raise ValueError("Specify either version or timestamp, not both")

    table_path = get_table_path(base_path, table_name)
    loop = asyncio.get_running_loop()

    try:
        if version is not None:
            return await loop.run_in_executor(
                None,
                lambda: delta_table_factory(table_path, version=version),
            )
        if timestamp is not None:
            timestamp_str = timestamp.isoformat()
            return await loop.run_in_executor(
                None,
                lambda: delta_table_factory(
                    table_path,
                    storage_options={"time_travel": timestamp_str},
                ),
            )
        raise ValueError("Must specify either version or timestamp")
    except DeltaTableNotFoundError as exc:
        raise TableNotFoundError(table_path) from exc


__all__ = ["load_time_travel_table"]
