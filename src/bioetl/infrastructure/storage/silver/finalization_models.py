"""Finalization request models for Silver write operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.types import BatchID, BronzeRecord
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult

__all__ = [
    "_SilverWriteFinalizationPreparationRequest",
    "_SilverWriteResultFinalizationRequest",
]


@dataclass(frozen=True, slots=True)
class _SilverWriteFinalizationPreparationRequest:
    """Normalized request payload for finalization context preparation."""

    table_name: str
    records: list[BronzeRecord]
    table_path: str
    started_at: datetime
    start_perf: float
    quarantined_count: int | None = None
    validation_errors: tuple[str, ...] | None = None
    primary_keys: list[str] | None = None
    validated_mode: SilverWriteMode | None = None


@dataclass(frozen=True, slots=True)
class _SilverWriteResultFinalizationRequest:
    """Normalized request payload for final Silver write result assembly."""

    table_name: str
    records: list[BronzeRecord]
    table_path: str
    primary_keys: list[str]
    validated_mode: SilverWriteMode
    bronze_refs: list[BronzeWriteResult] | None
    partition_cols: list[str] | None
    source_batch_id: BatchID | None
    started_at: datetime
    start_perf: float
    quarantined_count: int | None = None
    validation_errors: tuple[str, ...] | None = None
