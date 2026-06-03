"""Statistics functions for quarantine operations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:

    pass


def resolve_bucket_seconds(bucket: str) -> int:
    """Resolve bucket string to seconds."""
    normalized = bucket.strip().lower()
    mapping = {
        "1h": 3600,
        "6h": 21600,
        "1d": 86400,
    }
    if normalized not in mapping:
        raise ValueError(
            "Unsupported filtered-timeseries bucket. Allowed values: 1h, 6h, 1d"
        )
    return mapping[normalized]


def bucket_start_iso(value: object, *, bucket_seconds: int) -> str | None:
    """Convert timestamp to bucket start ISO string."""
    from bioetl.infrastructure.quarantine.filtered_read_support import (
        _normalize_timestamp,
    )

    _, parsed = _normalize_timestamp(value)
    if parsed is None:
        return None
    parsed_utc = parsed.astimezone(UTC)
    epoch_seconds = int(parsed_utc.timestamp())
    bucket_epoch_seconds = epoch_seconds - (epoch_seconds % bucket_seconds)
    return datetime.fromtimestamp(bucket_epoch_seconds, tz=UTC).isoformat()
