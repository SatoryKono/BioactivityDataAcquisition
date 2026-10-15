"""Audit helpers for Silver writer metadata paths."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.ports import AuditEntry, AuditLayer, AuditOperation, LoggerPort
from bioetl.domain.types import BatchID, BronzeRecord, RunID, RunType
from bioetl.infrastructure.storage.audit_normalization import (
    require_audit_run_id,
    require_audit_timestamp,
)

__all__ = ["_SilverAuditWriteRequest", "_build_silver_audit_entry"]

_SILVER_AUDIT_OPERATION_MAP: dict[SilverWriteMode, AuditOperation] = {
    SilverWriteMode.MERGE: AuditOperation.MERGE,
    SilverWriteMode.APPEND: AuditOperation.APPEND,
    SilverWriteMode.DELETE: AuditOperation.DELETE,
}


@dataclass(frozen=True, slots=True)
class _SilverAuditWriteRequest:
    """Normalized request payload for one Silver audit entry."""

    table_name: str
    records: list[BronzeRecord]
    mode: SilverWriteMode
    run_id: RunID | None = None
    run_type: RunType | None = None
    source_batch_id: BatchID | None = None
    ingestion_ts: datetime | None = None


class _SilverAuditHostProtocol(Protocol):
    """Minimal host contract for Silver audit entry construction."""

    @property
    def logger(self) -> LoggerPort: ...


def _build_silver_audit_entry(
    host: _SilverAuditHostProtocol,
    request: _SilverAuditWriteRequest,
) -> AuditEntry:
    """Build an AuditEntry for a Silver write operation.

    Silver audit is strict: ``run_id`` and ``ingestion_ts`` are required so the
    medallion traceability contract matches Gold.
    """
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

    operation = _SILVER_AUDIT_OPERATION_MAP[request.mode]

    return AuditEntry(
        run_id=audit_run_id,
        timestamp=timestamp,
        layer=AuditLayer.SILVER,
        table_name=request.table_name,
        operation=operation,
        records_count=len(request.records),
        metadata={
            "run_type": (
                str(getattr(request.run_type, "value", request.run_type))
                if request.run_type is not None
                else ""
            ),
            "source_batch_id": (
                str(request.source_batch_id)
                if request.source_batch_id is not None
                else ""
            ),
        },
    )
