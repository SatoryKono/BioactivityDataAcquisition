"""Identity and timestamp helpers for export sidecar manifests."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bioetl.domain.ports import ExportFileFingerprint

if TYPE_CHECKING:
    from bioetl.domain.ports import ClockPort


def dataset_bundle_id(
    *,
    table_name: str,
    layer: str,
    export_format: str,
    row_count: int,
    columns: tuple[str, ...],
    providers: tuple[str, ...],
    data_sha256: str,
) -> str:
    """Build a deterministic dataset bundle identifier."""
    payload = {
        "columns": list(columns),
        "data_sha256": data_sha256,
        "export_format": export_format,
        "layer": layer,
        "providers": list(providers),
        "row_count": row_count,
        "table_name": table_name,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
    return f"bioetl-export-{digest}"


def fingerprint_payload(fingerprint: ExportFileFingerprint) -> dict[str, object]:
    """Project a file fingerprint into manifest-safe JSON fields."""
    path_str = fingerprint.path if isinstance(fingerprint.path, str) else fingerprint.path.as_posix()
    return {
        "path": path_str,
        "size_bytes": fingerprint.size_bytes,
        "sha256": fingerprint.sha256,
    }


def resolve_generated_at(
    generated_at: str | None,
    *,
    allow_nondeterministic: bool,
    clock: ClockPort | None,
) -> str:
    """Resolve export manifest timestamp without implicit wall-clock drift."""
    if generated_at is not None:
        timestamp = generated_at.strip()
        if timestamp:
            return timestamp
    if allow_nondeterministic:
        if clock is not None:
            return format_utc(clock.now())
        return utc_now()
    raise ValueError(
        "generated_at must be provided for deterministic export manifests; "
        "operator-only exports must opt into non-deterministic generated_at"
    )


def utc_now() -> str:
    """Return the current UTC time in manifest timestamp format."""
    return format_utc(datetime.now(UTC))


def format_utc(value: datetime) -> str:
    """Format one datetime as a second-granularity UTC timestamp."""
    return (
        value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )


__all__ = [
    "dataset_bundle_id",
    "fingerprint_payload",
    "format_utc",
    "resolve_generated_at",
    "utc_now",
]
