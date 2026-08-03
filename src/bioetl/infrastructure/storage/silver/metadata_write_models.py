"""Standard Silver metadata write request models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.types import BronzeRecord
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics

__all__ = ["_SilverMetadataWriteRequest"]


@dataclass(frozen=True, slots=True)
class _SilverMetadataWriteRequest:
    """Normalized request payload for one standard Silver metadata write."""

    table_path: str
    table_name: str
    records: list[BronzeRecord]
    primary_keys: list[str]
    mode: SilverWriteMode
    bronze_refs: list[BronzeWriteResult] | None = None
    dq_metrics: BatchDQMetrics | None = None
    dq_report_path: str | None = None
    partition_by: list[str] | None = None
    source_batch_ids: list[str] | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    version_after: int | None = None
