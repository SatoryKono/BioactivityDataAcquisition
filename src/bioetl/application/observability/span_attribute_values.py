"""Helpers for OpenTelemetry-compatible span attribute coercion."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeAlias

SpanAttributeValue: TypeAlias = (
    str
    | bool
    | int
    | float
    | Sequence[str]
    | Sequence[bool]
    | Sequence[int]
    | Sequence[float]
)


def _sequence_items(value: object) -> list[object] | None:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        return None
    return list(value)


def _string_sequence(items: list[object]) -> Sequence[str] | None:
    if not items:
        return ()
    if all(isinstance(item, str) for item in items):
        return [item for item in items if isinstance(item, str)]
    return None


def _bool_sequence(items: list[object]) -> Sequence[bool] | None:
    if not items:
        return ()
    if all(isinstance(item, bool) for item in items):
        return [item for item in items if isinstance(item, bool)]
    return None


def _int_sequence(items: list[object]) -> Sequence[int] | None:
    if not items:
        return ()
    if all(isinstance(item, int) and not isinstance(item, bool) for item in items):
        return [
            item
            for item in items
            if isinstance(item, int) and not isinstance(item, bool)
        ]
    return None


def _float_sequence(items: list[object]) -> Sequence[float] | None:
    if not items:
        return ()
    if all(isinstance(item, float) for item in items):
        return [item for item in items if isinstance(item, float)]
    return None


def coerce_span_attribute_value(value: object) -> SpanAttributeValue:
    """Convert arbitrary metadata into OpenTelemetry-compatible values."""
    if isinstance(value, bool | str | int | float):
        return value

    items = _sequence_items(value)
    if items is None:
        return str(value)

    for matcher in (
        _string_sequence,
        _bool_sequence,
        _int_sequence,
        _float_sequence,
    ):
        matched = matcher(items)
        if matched is not None:
            return matched

    return str(value)


__all__ = ["SpanAttributeValue", "coerce_span_attribute_value"]
