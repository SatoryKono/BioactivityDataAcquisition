"""Presentation-only identity values; raw evidence remains available for copying."""

from __future__ import annotations

from datetime import datetime
from math import isfinite
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_CLOCK_PARAMETERS = frozenset({"Started at", "Completed at"})


def identity_display_rows(rows: object, timezone: str) -> list[dict[str, str]]:
    """Format clocks in the dashboard zone without changing raw identity rows."""
    zone = _resolve_zone(timezone)
    result: list[dict[str, str]] = []
    if not isinstance(rows, list):
        return result
    for item in rows:
        if not isinstance(item, dict):
            continue
        parameter = str(item.get("parameter", ""))
        raw = str(item.get("value", ""))
        value = raw
        if parameter in _CLOCK_PARAMETERS:
            value = _format_clock(raw, zone)
        elif parameter == "Duration seconds":
            formatted = _format_duration(raw)
            if formatted is not None:
                value = formatted
                parameter = "Duration"
        result.append({"parameter": parameter, "value": value, "raw_value": raw})
    return result


def _resolve_zone(timezone: str) -> ZoneInfo:
    token = timezone.strip() or "UTC"
    if token.lower() in {"utc", "browser", "default"}:
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(token)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def _format_clock(raw: str, zone: ZoneInfo) -> str:
    try:
        moment = datetime.fromisoformat(raw)
    except ValueError:
        return raw
    if moment.tzinfo is None:
        return raw
    return moment.astimezone(zone).strftime("%Y-%m-%d %H:%M %Z")


def _format_duration(raw: str) -> str | None:
    try:
        seconds = float(raw)
    except ValueError:
        return None
    if not isfinite(seconds) or seconds < 0:
        return None
    minutes, remainder = divmod(round(seconds), 60)
    return f"{minutes} min {remainder:02d} s"
