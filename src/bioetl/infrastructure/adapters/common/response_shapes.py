"""Shared response-shaping helpers for infrastructure adapters."""

from __future__ import annotations

from collections.abc import Mapping

__all__ = [
    "extract_response_items",
    "extract_response_mapping",
    "extract_response_text",
    "normalize_response_items",
]


def normalize_response_items(items: object) -> list[object]:
    """Normalize list-like adapter payload items to a concrete list."""
    if isinstance(items, list):
        return items
    if isinstance(items, tuple):
        return list(items)
    return []


def extract_response_items(
    payload: Mapping[str, object],
    key: str,
) -> list[object]:
    """Return normalized list-like items from a payload field."""
    return normalize_response_items(payload.get(key))


def extract_response_mapping(
    payload: Mapping[str, object],
    key: str,
) -> Mapping[str, object] | None:
    """Return nested mapping field when present and well-formed."""
    raw_value = payload.get(key)
    if isinstance(raw_value, Mapping):
        return raw_value
    return None


def extract_response_text(
    payload: Mapping[str, object],
    key: str,
) -> str | None:
    """Return text field when present and well-formed."""
    raw_value = payload.get(key)
    if isinstance(raw_value, str):
        return raw_value
    return None
