"""Audit helpers for Gold writer metadata paths."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from bioetl.domain.medallion import GoldWriteMode
from bioetl.domain.ports import AuditEntry, AuditLayer, AuditOperation, LoggerPort
from bioetl.domain.types import GoldRecord, RunID
from bioetl.infrastructure.storage.audit_normalization import (
    require_audit_run_id,
    require_audit_timestamp,
)

__all__ = ["_GoldAuditWriteRequest", "_build_gold_audit_entry"]


@dataclass(frozen=True, slots=True)
class _GoldAuditWriteRequest:
    table_name: str
    records: list[GoldRecord]
    mode: GoldWriteMode
    ingestion_ts: datetime | None
    run_id: RunID | None


class _GoldMetadataAuditHostProtocol(Protocol):
    logger: LoggerPort


def _build_gold_audit_entry(
    host: _GoldMetadataAuditHostProtocol,
    request: _GoldAuditWriteRequest,
) -> AuditEntry:
    timestamp = require_audit_timestamp(
        logger=host.logger,
        timestamp=request.ingestion_ts,
        table_name=request.table_name,
        mode=request.mode.value,
    )
    audit_run_id = require_audit_run_id(
        logger=host.logger,
        run_id=request.run_id,
        table_name=request.table_name,
        mode=request.mode.value,
    )

    operation_map = {
        GoldWriteMode.OVERWRITE: AuditOperation.OVERWRITE,
        GoldWriteMode.APPEND: AuditOperation.APPEND,
        GoldWriteMode.SCD2: AuditOperation.MERGE,
    }

    return AuditEntry(
        run_id=audit_run_id,
        timestamp=timestamp,
        layer=AuditLayer.GOLD,
        table_name=request.table_name,
        operation=operation_map[request.mode],
        records_count=len(request.records),
        metadata={"write_mode": request.mode.value},
    )
