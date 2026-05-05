"""Shared models for quarantine admin services and mixins."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bioetl.domain.types import JsonDict


@dataclass(frozen=True, slots=True)
class QuarantineRecord:
    """Representation of a quarantined record."""

    error_code: str | None
    payload: JsonDict
    batch_id: str | None
    pipeline: str
    ingestion_ts: datetime | None
    metadata: JsonDict


__all__ = ["QuarantineRecord"]
