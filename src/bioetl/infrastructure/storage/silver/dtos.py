"""Data Transfer Objects for Silver layer operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pyarrow as pa


@dataclass(frozen=True, slots=True)
class ValidatedSilverWriteContext:
    """Context containing validated data ready for Silver layer write."""

    arrow_table: pa.Table
    metadata: dict[str, Any]  # Any: Flexible metadata structure from various sources
    validation_timestamp: datetime
    write_mode: str
    table_name: str


@dataclass(frozen=True, slots=True)
class SilverWriteResult:
    """Result of a Silver layer write operation."""

    table_name: str
    records_written: int
    write_duration_seconds: float
    metadata_written: bool
    records_updated: int | None = None
    records_deleted: int | None = None


@dataclass(frozen=True, slots=True)
class SilverMaintenanceContext:
    """Context for Silver layer maintenance operations."""

    table_name: str
    operation_type: str  # 'vacuum', 'optimize', 'export'
    operation_params: dict[
        str,
        Any,  # Any: Flexible operation parameters for different maintenance tasks
    ]
