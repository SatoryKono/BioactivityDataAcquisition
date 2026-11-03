"""Serialization helpers for run-report value models."""

from __future__ import annotations

from typing import Any


def _copy_present_attributes(
    payload: dict[str, Any],  # Any: dynamic report serialization payload
    source: object,
    names: tuple[str, ...],
) -> None:
    """Copy non-null attributes into a dynamic report payload."""
    for name in names:
        value = getattr(source, name)
        if value is not None:
            payload[name] = value


def _copy_present_mappings(
    payload: dict[str, Any],  # Any: dynamic report serialization payload
    source: object,
    names: tuple[str, ...],
) -> None:
    """Copy non-null mapping attributes into a dynamic report payload."""
    for name in names:
        value = getattr(source, name)
        if value is not None:
            payload[name] = dict(value)


def _copy_reason_items(
    payload: dict[str, Any],  # Any: dynamic report serialization payload
    name: str,
    items: tuple[dict[str, Any], ...],  # Any: dynamic reason payload
) -> None:
    """Copy a non-empty tuple of dynamic reason mappings."""
    if items:
        payload[name] = [dict(item) for item in items]
