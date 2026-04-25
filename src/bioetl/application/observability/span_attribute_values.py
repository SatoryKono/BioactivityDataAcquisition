"""Helpers for OpenTelemetry-compatible span attribute coercion."""

from __future__ import annotations

from collections.abc import Callable, Sequence
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


def _matching_sequence(
    items: list[object],
    predicate: Callable[[object], bool],
) -> SpanAttributeValue | None:
    if not items:
        return []
    if all(predicate(item) for item in items):
        return items
    return None


def coerce_span_attribute_value(value: object) -> SpanAttributeValue:
    """Convert arbitrary metadata into OpenTelemetry-compatible values."""
    if isinstance(value, bool | str | int | float):
        return value

    items = _sequence_items(value)
    if items is None:
        return str(value)

    for predicate in (
        lambda item: isinstance(item, str),
        lambda item: isinstance(item, bool),
        lambda item: isinstance(item, int) and not isinstance(item, bool),
        lambda item: isinstance(item, float),
    ):
        matched = _matching_sequence(items, predicate)
        if matched is not None:
            return matched

    return str(value)


__all__ = ["SpanAttributeValue", "coerce_span_attribute_value"]
