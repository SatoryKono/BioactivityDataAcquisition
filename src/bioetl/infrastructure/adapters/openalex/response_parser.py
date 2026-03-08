"""OpenAlex response parsing helpers."""

from __future__ import annotations

from bioetl.domain.types import BronzeRecord, JsonDict


def parse_openalex_results(
    payload: JsonDict,  # Any: untyped OpenAlex API payload
) -> list[BronzeRecord]:
    """Extract `results` list from OpenAlex payload.

    Args:
        payload: Raw OpenAlex API JSON response payload.

    Returns:
        List of BronzeRecord dictionaries from the results array, or empty list if absent.
    """
    raw_results = payload.get("results")
    if isinstance(raw_results, list):
        return raw_results
    return []


def parse_openalex_next_cursor(
    payload: JsonDict,  # Any: untyped OpenAlex API payload
) -> str | None:
    """Extract next cursor from OpenAlex payload meta.

    Args:
        payload: Raw OpenAlex API JSON response payload.

    Returns:
        Next cursor string if present in meta, None if last page or meta is absent.
    """
    raw_meta = payload.get("meta")
    if not isinstance(raw_meta, dict):
        return None
    raw_cursor = raw_meta.get("next_cursor")
    if isinstance(raw_cursor, str):
        return raw_cursor
    return None


__all__ = [
    "parse_openalex_next_cursor",
    "parse_openalex_results",
]
