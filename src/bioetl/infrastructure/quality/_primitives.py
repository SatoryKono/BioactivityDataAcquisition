"""Shared primitive validators and parsers for debt scorecard validation."""

from __future__ import annotations

import re
from datetime import date
from typing import TypedDict

_QUARTER_RE = re.compile(r"^(20\d{2})-Q([1-4])$")


class QuarterTarget(TypedDict):
    """Normalized quarterly target entry."""

    quarter: str
    max_total_exemptions: int
    min_integral_score: int | float
    group_budgets: dict[str, int]
    registry_budgets: dict[str, int]


def _parse_iso_date(raw_value: object) -> date | None:
    if not isinstance(raw_value, str):
        return None
    try:
        return date.fromisoformat(raw_value)
    except ValueError:
        return None


def _parse_quarter_label(value: str) -> tuple[int, int] | None:
    match = _QUARTER_RE.fullmatch(value.strip())
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))


def _quarter_label(target_date: date) -> str:
    quarter = ((target_date.month - 1) // 3) + 1
    return f"{target_date.year}-Q{quarter}"


def _validate_non_negative_int(
    value: object,
    *,
    field_name: str,
    errors: list[str],
) -> int | None:
    if not isinstance(value, int):
        errors.append(f"{field_name}: expected int, got {type(value).__name__}")
        return None
    if value < 0:
        errors.append(f"{field_name}: expected non-negative int, got {value}")
        return None
    return value


def _validate_gate_mode(
    *,
    value: object,
    field_name: str,
    errors: list[str],
) -> str | None:
    if not isinstance(value, str):
        errors.append(f"{field_name}: expected string ('warn' or 'block')")
        return None
    mode = value.strip().lower()
    if mode not in {"warn", "block"}:
        errors.append(f"{field_name}: expected 'warn' or 'block', got {value!r}")
        return None
    return mode


def _validate_budget_mapping(
    mapping: object,
    *,
    expected_keys: set[str],
    field_name: str,
    errors: list[str],
) -> None:
    if not isinstance(mapping, dict):
        errors.append(f"{field_name}: expected mapping")
        return

    missing_keys = sorted(expected_keys - set(mapping))
    extra_keys = sorted(set(mapping) - expected_keys)
    if missing_keys:
        errors.append(f"{field_name}: missing entries {missing_keys}")
    if extra_keys:
        errors.append(f"{field_name}: unknown entries {extra_keys}")

    for key, value in mapping.items():
        _validate_non_negative_int(
            value,
            field_name=f"{field_name}.{key}",
            errors=errors,
        )
