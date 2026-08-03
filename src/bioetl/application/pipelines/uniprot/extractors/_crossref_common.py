"""Shared helpers for UniProt cross-reference extraction."""

from __future__ import annotations

from collections.abc import Sequence

from bioetl.domain.serialization import serialize_to_json
from bioetl.domain.types import JsonDict


def parse_properties(properties: object) -> dict[str, str]:
    """Parse cross-reference properties into a key-value mapping.

    Args:
        properties: Raw properties value from a UniProt cross-reference dict.
            Expected to be a list of dicts with 'key' and 'value' string fields.

    Returns:
        Dict mapping property key strings to their value strings.
        Returns empty dict if properties is not a list or contains no valid entries.
    """
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
    """Return cross-references belonging to the requested database.

    Args:
        xrefs: List of UniProt cross-reference dicts from the API response, or None.
        database: Database name string to filter on (e.g. 'PDB', 'InterPro').

    Returns:
        Filtered list of cross-reference dicts whose 'database' field matches.
        Returns empty list if xrefs is None, not a list, or no matches found.
    """
    if not xrefs or not isinstance(xrefs, list):
        return []

    return [
        xref
        for xref in xrefs
        if isinstance(xref, dict) and xref.get("database") == database
    ]


def serialize_json_or_none(data: Sequence[object]) -> str | None:
    """Serialize JSON-compatible list or return None for empty payload.

    Args:
        data: Sequence of JSON-serializable objects to encode.

    Returns:
        JSON-encoded string of data, or None if data is empty.
    """
    return serialize_to_json(data, ensure_ascii=False) if data else None
