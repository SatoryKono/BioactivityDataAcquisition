"""Audit helpers for Silver writer metadata paths.

Extracted from ``SilverWriterMetadataMixin`` to localise the audit axis:
RunID parsing, timestamp normalization, operation mapping and AuditEntry
construction are isolated here so that changes to audit handling do not
ripple through the wider metadata / DQ / finalization pipeline.

Mirrors the established pattern of ``gold/metadata_audit.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.ports import AuditEntry, AuditLayer, AuditOperation, LoggerPort
from bioetl.domain.types import BatchID, BronzeRecord, RunID, RunType

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

    logger: LoggerPort


def _build_silver_audit_entry(
    host: _SilverAuditHostProtocol,
    request: _SilverAuditWriteRequest,
) -> AuditEntry | None:
    """Build an AuditEntry for a Silver write operation.

    Returns ``None`` when no valid explicit ``run_id`` is available.
    """
    if request.run_id is None:
        host.logger.warning(
            "audit_skipped_invalid_run_id",
            table=request.table_name,
            run_id="",
        )
        return None

    timestamp = request.ingestion_ts or datetime.fromtimestamp(0, tz=UTC)

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)

    operation = _SILVER_AUDIT_OPERATION_MAP[request.mode]

    return AuditEntry(
        run_id=request.run_id,
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
