"""OpenAlex response parsing helpers."""

from __future__ import annotations

from bioetl.domain.types import BronzeRecord, JsonDict
from bioetl.infrastructure.adapters.openalex.response_mapping import (
    OpenAlexResponseMapper,
)

_RESPONSE_MAPPER = OpenAlexResponseMapper()


def parse_openalex_results(
    payload: JsonDict,  # Any: untyped OpenAlex API payload
) -> list[BronzeRecord]:
    """Compatibility shim for extracting `results` from OpenAlex payloads.

    Args:
        payload: Raw OpenAlex API JSON response payload.

    Returns:
        List of BronzeRecord dictionaries from the results array, or empty list if absent.
    """
    return _RESPONSE_MAPPER.extract_results(payload)


def parse_openalex_next_cursor(
    payload: JsonDict,  # Any: untyped OpenAlex API payload
) -> str | None:
    """Compatibility shim for extracting next cursor from OpenAlex payload meta.

    Args:
        payload: Raw OpenAlex API JSON response payload.

    Returns:
        Next cursor string if present in meta, None if last page or meta is absent.
    """
    return _RESPONSE_MAPPER.extract_next_cursor(payload)


__all__ = [
    "parse_openalex_next_cursor",
    "parse_openalex_results",
]
