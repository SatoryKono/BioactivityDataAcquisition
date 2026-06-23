"""Shared audit normalization helpers for medallion storage writers."""

from __future__ import annotations

from datetime import datetime

from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import RunID

__all__ = ["require_audit_run_id", "require_audit_timestamp"]


def require_audit_timestamp(
    *,
    logger: LoggerPort,
    timestamp: datetime | None,
    table_name: str,
    mode: str,
) -> datetime:
    """Return one validated audit timestamp or fail deterministically."""
    if timestamp is None:
        logger.warning(
            "audit_missing_ingestion_ts",
            table=table_name,
            mode=mode,
        )
        raise ValueError("ingestion_ts is required for audit logging")
    if timestamp.tzinfo is None:
        raise ValueError("ingestion_ts must be timezone-aware")
    return timestamp


def require_audit_run_id(
    *,
    logger: LoggerPort,
    run_id: RunID | None,
    table_name: str,
    mode: str,
) -> RunID:
    """Return one validated audit run identifier or fail deterministically."""
    if run_id is None:
        logger.warning(
            "audit_missing_run_id",
            table=table_name,
            mode=mode,
        )
        raise ValueError("run_id is required for audit logging")
    return run_id
