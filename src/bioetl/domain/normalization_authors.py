"""Author-list parsing and extraction helpers."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any  # Any: used for list[Any] in JSON parsing results

from bioetl.domain.serialization import deserialize_from_json

__all__ = [
    "extract_first_item",
    "extract_first_string",
    "parse_authors_to_list",
]


def extract_first_item(items: list[object] | None) -> object | None:
    """Extract first non-None item from list.

    Args:
        items: List of objects or None.

    Returns:
        First non-None element from the list, or None if list is empty or invalid.
    """
    if not items or not isinstance(items, list):
        return None
    return next((item for item in items if item is not None), None)


def _is_valid_string(item: object) -> str | None:
    """Return stripped string if non-empty, else None."""
    return str(item).strip() if item is not None else None


def extract_first_string(items: list[str] | None) -> str | None:
    """Extract first non-empty stripped string from list.

    Args:
        items: List of strings or None.

    Returns:
        First non-empty stripped string, or None if no valid string is found.
    """
    if not items or not isinstance(items, list):
        return None
    return next((s for item in items if (s := _is_valid_string(item))), None)


def _filter_valid_strings(items: list[object]) -> list[str]:
    """Filter list to valid non-empty strings."""
    return [str(a).strip() for a in items if a is not None and str(a).strip()]


def _parse_authors_from_list(authors: Sequence[object]) -> list[str]:
    """Parse author list, filtering non-strings and empty values."""
    return [a.strip() for a in authors if isinstance(a, str) and a.strip()]


def _try_parse_json_array(
    text: str,
) -> list[Any] | None:  # Any: JSON parse result type varies
    """Try to parse text as JSON array. Returns None if invalid."""
    try:
        parsed = deserialize_from_json(text)
        return parsed if isinstance(parsed, list) else None
    except ValueError:
        return None


def _parse_authors_from_json(text: str) -> list[str] | None:
    """Try to parse JSON array of authors. Returns None if not valid JSON."""
    if not text.startswith("["):
        return None
    parsed = _try_parse_json_array(text)
    return _filter_valid_strings(parsed) if parsed is not None else None


def _parse_authors_from_delimited(text: str) -> list[str]:
    """Parse delimited string (semicolon or comma separated)."""
    delimiter = ";" if ";" in text else ","
    parts = text.split(delimiter) if delimiter in text else [text]
    return [a.strip() for a in parts if a.strip()]


def _parse_authors_string(text: str) -> list[str]:
    """Parse string as JSON or delimited format."""
    json_result = _parse_authors_from_json(text)
    return (
        json_result if json_result is not None else _parse_authors_from_delimited(text)
    )


def parse_authors_to_list(authors: list[str] | str | None) -> list[str]:
    """Parse author input (list, JSON string, or delimited string) to list.

    Args:
        authors: Author data as a list of strings, a JSON array string, a
            semicolon/comma-delimited string, or None.

    Returns:
        List of non-empty stripped author name strings. Returns empty list if
        input is None or contains no valid authors.
    """
    if authors is None:
        return []
    if isinstance(authors, list):
        return _parse_authors_from_list(authors)
    if isinstance(authors, str) and authors.strip():
        return _parse_authors_string(authors.strip())
    return []
