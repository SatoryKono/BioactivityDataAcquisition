"""DQ condition matcher functions.

Extracted from _dq_rule_evaluators.py to meet file size limits.
"""

from __future__ import annotations


def _eq_condition_matches(
    value: object,
    condition_value: str | tuple[str, ...],
) -> bool:
    return value == condition_value


def _ne_condition_matches(
    value: object,
    condition_value: str | tuple[str, ...],
) -> bool:
    return value != condition_value


def _in_condition_matches(
    value: object,
    condition_value: str | tuple[str, ...],
) -> bool:
    return value in _condition_options(condition_value)


def _not_in_condition_matches(
    value: object,
    condition_value: str | tuple[str, ...],
) -> bool:
    return value not in _condition_options(condition_value)


def _condition_options(condition_value: str | tuple[str, ...]) -> tuple[str, ...]:
    if isinstance(condition_value, tuple):
        return condition_value
    return (condition_value,)


_CONDITIONAL_MATCHERS = {
    "eq": _eq_condition_matches,
    "ne": _ne_condition_matches,
    "in": _in_condition_matches,
    "not_in": _not_in_condition_matches,
}


__all__ = [
    "_CONDITIONAL_MATCHERS",
    "_condition_options",
    "_eq_condition_matches",
    "_in_condition_matches",
    "_ne_condition_matches",
    "_not_in_condition_matches",
]
