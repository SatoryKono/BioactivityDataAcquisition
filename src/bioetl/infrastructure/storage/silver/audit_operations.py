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
from uuid import UUID

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.ports import AuditEntry, AuditLayer, AuditOperation, LoggerPort
from bioetl.domain.types import BronzeRecord, RunID

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


class _SilverAuditHostProtocol(Protocol):
    """Minimal host contract for Silver audit entry construction."""

    logger: LoggerPort


def _build_silver_audit_entry(
    host: _SilverAuditHostProtocol,
    request: _SilverAuditWriteRequest,
) -> AuditEntry | None:
    """Build an AuditEntry for a Silver write operation.

    Returns ``None`` when the first record contains an invalid ``_run_id``
    (mirrors the original skip-with-warning behaviour).
    """
    first_record = request.records[0]
    run_id_str = first_record.get("_run_id", "")
    ingestion_ts = first_record.get("_ingestion_ts")

    try:
        run_id = RunID(UUID(run_id_str))
    except (ValueError, TypeError):
        host.logger.warning(
            "audit_skipped_invalid_run_id",
            table=request.table_name,
            run_id=run_id_str,
        )
        return None

    if isinstance(ingestion_ts, str):
        timestamp = datetime.fromisoformat(ingestion_ts)
    elif isinstance(ingestion_ts, datetime):
        timestamp = ingestion_ts
    else:
        timestamp = datetime.fromtimestamp(0, tz=UTC)

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)

    operation = _SILVER_AUDIT_OPERATION_MAP[request.mode]

    return AuditEntry(
        run_id=run_id,
        timestamp=timestamp,
        layer=AuditLayer.SILVER,
        table_name=request.table_name,
        operation=operation,
        records_count=len(request.records),
        metadata={
            "run_type": first_record.get("_run_type", ""),
            "source_batch_id": first_record.get("_source_batch_id", ""),
        },
    )
