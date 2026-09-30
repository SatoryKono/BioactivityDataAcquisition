"""Shared quarantine entry value types for runtime write paths."""

from __future__ import annotations

from typing import NamedTuple

from bioetl.domain.types import BronzeRecord, ErrorType, JsonDict


class DQQuarantineEntry(NamedTuple):
    """A record that failed data-quality checks."""

    record: BronzeRecord
    error_type: ErrorType
    error_details: str
    reason_code: str | None = None


class FilteredQuarantineEntry(NamedTuple):
    """A record excluded by Silver filters."""

    record: BronzeRecord
    reason: str
    details: JsonDict | None = None


__all__ = [
    "DQQuarantineEntry",
    "FilteredQuarantineEntry",
]
