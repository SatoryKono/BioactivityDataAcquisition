"""Small value/selector helpers for the Processed Records HTTP surface."""

from __future__ import annotations

import math
import re

_ALL_SCOPE_TOKENS = frozenset({"All", "$__all", "__all", "*"})


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
    if not normalized or normalized in _ALL_SCOPE_TOKENS:
        return ()
    if normalized.startswith("{") and normalized.endswith("}"):
        normalized = normalized[1:-1]

    tokens: list[str] = []
    for part in normalized.split(","):
        token = part.strip()
        if not token or token in _ALL_SCOPE_TOKENS:
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
        return "No data"
    rounded = round(value)
    if math.isclose(value, rounded, abs_tol=1e-9):
        return f"{int(rounded):,}".replace(",", " ")
    return str(value)
