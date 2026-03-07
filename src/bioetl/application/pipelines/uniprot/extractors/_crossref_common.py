"""Shared helpers for UniProt cross-reference extraction."""

from __future__ import annotations

from collections.abc import Sequence

from bioetl.domain.serialization import serialize_to_json
from bioetl.domain.types import JsonDict


def parse_properties(properties: object) -> dict[str, str]:
    """Parse cross-reference properties into a key-value mapping."""
    if not isinstance(properties, list):
        return {}

    parsed: dict[str, str] = {}
    for prop in properties:
        if not isinstance(prop, dict):
            continue
        key = prop.get("key")
        value = prop.get("value")
        if isinstance(key, str) and key and isinstance(value, str) and value:
            parsed[key] = value
    return parsed


def filter_xrefs_by_database(
    xrefs: list[JsonDict] | None,
    database: str,
) -> list[JsonDict]:
    """Return cross-references belonging to the requested database."""
    if not xrefs or not isinstance(xrefs, list):
        return []

    return [
        xref
        for xref in xrefs
        if isinstance(xref, dict) and xref.get("database") == database
    ]


def serialize_json_or_none(data: Sequence[object]) -> str | None:
    """Serialize JSON-compatible list or return None for empty payload."""
    return serialize_to_json(data, ensure_ascii=False) if data else None
