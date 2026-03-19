"""Audit helpers for Gold writer metadata paths."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from bioetl.domain.medallion import GoldWriteMode
from bioetl.domain.ports import AuditEntry, AuditLayer, AuditOperation, LoggerPort
from bioetl.domain.types import GoldRecord, RunID

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
    from uuid import uuid4

    if request.ingestion_ts is not None:
        timestamp = request.ingestion_ts
    else:
        host.logger.warning(
            "audit_missing_ingestion_ts",
            table=request.table_name,
            mode=request.mode.value,
        )
        raise ValueError("ingestion_ts is required for audit logging")

    if request.run_id is not None:
        audit_run_id = request.run_id
    else:
        host.logger.warning(
            "audit_missing_run_id",
            table=request.table_name,
            mode=request.mode.value,
        )
        audit_run_id = RunID(uuid4())

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
