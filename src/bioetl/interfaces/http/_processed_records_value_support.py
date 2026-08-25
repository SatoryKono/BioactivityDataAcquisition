"""Small value/selector helpers for the Processed Records HTTP surface."""

from __future__ import annotations

import math
import re
from datetime import UTC, datetime, timedelta

_ALL_SCOPE_EXACT_TOKENS = frozenset({"$__all", "__all", ".*"})


def _is_all_scope(value: str | None) -> bool:
    """Return True for Grafana All-scope tokens, including lowercase ``all``."""
    if value is None:
        return False
    normalized = value.strip()
    if not normalized:
        return False
    lowered = normalized.casefold()
    return lowered in {"all", "*"} or normalized in _ALL_SCOPE_EXACT_TOKENS


def _selector_regex(raw: str | None) -> str:
    tokens = _selector_tokens(raw)
    if not tokens:
        return ".*"
    if len(tokens) == 1:
        return re.escape(tokens[0])
    return "(?:" + "|".join(re.escape(token) for token in tokens) + ")"


def _selector_tokens(raw: str | None) -> tuple[str, ...]:
    if raw is None:
        return ()
    normalized = raw.strip()
    if not normalized or _is_all_scope(normalized):
        return ()
    if normalized.startswith("{") and normalized.endswith("}"):
        normalized = normalized[1:-1]

    tokens: list[str] = []
    for part in normalized.split(","):
        token = part.strip()
        if not token or _is_all_scope(token):
            return ()
        if token not in tokens:
            tokens.append(token)
    return tuple(tokens)


def _promql_string(raw: str) -> str:
    """Escape a value for embedding in a double-quoted PromQL string literal."""
    return (
        raw.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace('"', '\\"')
    )


def _as_float(value: float | int | None) -> float | None:
    if value is None:
        return None
    parsed = float(value)
    if not math.isfinite(parsed):
        return None
    return parsed


def _optional_text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: object | None) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if not isinstance(value, (str, bytes, bytearray, int, float)):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _sum_metric_values(
    metric_values: dict[str, float | int | None], metrics: tuple[str, ...]
) -> float | None:
    values = tuple(_as_float(metric_values.get(metric)) for metric in metrics)
    if any(value is None for value in values):
        return None
    return sum(value for value in values if value is not None)


def is_deficit(*, total: float | None, minimum: float | None) -> bool:
    return total is not None and minimum is not None and total < minimum


def _count_text(value: float | None) -> str:
    if value is None:
        return "UNKNOWN"
    rounded = round(value)
    if math.isclose(value, rounded, abs_tol=1e-9):
        return f"{int(rounded):,}".replace(",", " ")
    return str(value)


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
