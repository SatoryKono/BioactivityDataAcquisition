"""Coverage and Grafana range helpers for pipeline run report tables."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

_RANGE_PAD = timedelta(minutes=5)


def _parse_iso_to_ms(value: object) -> int | None:
    """Parse an ISO-8601 timestamp to Unix milliseconds."""
    if not isinstance(value, str) or not value.strip():
        return None
    token = value.strip()
    if token.endswith("Z"):
        token = token[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(token)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return int(parsed.timestamp() * 1000)


def _parse_grafana_ms(value: object) -> int | None:
    """Parse Grafana ${__from}/${__to} epoch-ms query parameters."""
    if value is None:
        return None
    token = str(value).strip()
    if not token:
        return None
    try:
        return int(token)
    except ValueError:
        return None


def _coverage_offset_outside(
    *,
    started_ms: int,
    end_ms: int,
    grafana_from_ms: int,
    grafana_to_ms: int,
) -> tuple[str, str]:
    """Describe a run that is not fully inside the Grafana window."""
    if end_ms < grafana_from_ms:
        hours = (grafana_from_ms - end_ms) / 3_600_000
        return "outside", f"{hours:.1f}h before window"
    if started_ms > grafana_to_ms:
        hours = (started_ms - grafana_to_ms) / 3_600_000
        return "outside", f"{hours:.1f}h after window"
    return "partial", "overlaps window"


def _coverage_chip(covers: str) -> str:
    """Map coverage projection to the first-window IN RANGE / OUT OF RANGE chip."""
    if covers == "yes":
        return "IN RANGE"
    if covers in {"outside", "partial"}:
        return "OUT OF RANGE"
    return "UNKNOWN"


def _coverage_fields(
    *,
    started_ms: int | None,
    completed_ms: int | None,
    grafana_from_ms: int | None,
    grafana_to_ms: int | None,
    status: str,
) -> tuple[str, str]:
    """Return (covers_selected_run, coverage_offset) for the compact summary."""
    if status == "unresolved_scope":
        return "select_run", ""
    if status == "not_found":
        return "not_found", ""
    if started_ms is None:
        return "unknown", ""
    if grafana_from_ms is None or grafana_to_ms is None:
        return "range_unspecified", ""
    end_ms = completed_ms if completed_ms is not None else started_ms
    if started_ms >= grafana_from_ms and end_ms <= grafana_to_ms:
        return "yes", "0h"
    return _coverage_offset_outside(
        started_ms=started_ms,
        end_ms=end_ms,
        grafana_from_ms=grafana_from_ms,
        grafana_to_ms=grafana_to_ms,
    )


def _padded_range_ms(
    started_ms: int | None, completed_ms: int | None
) -> tuple[str, str]:
    """Return padded from/to epoch-ms strings for Grafana range links."""
    if started_ms is None:
        return "", ""
    pad_ms = int(_RANGE_PAD.total_seconds() * 1000)
    end_ms = completed_ms if completed_ms is not None else started_ms
    return str(started_ms - pad_ms), str(end_ms + pad_ms)
