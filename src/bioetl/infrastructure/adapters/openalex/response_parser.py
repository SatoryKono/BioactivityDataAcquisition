"""OpenAlex response parsing compatibility exports."""

from __future__ import annotations

from bioetl.infrastructure.adapters.openalex.response_mapping import (
    OpenAlexResponseMapper,
)

_RESPONSE_MAPPER = OpenAlexResponseMapper()
parse_openalex_results = _RESPONSE_MAPPER.extract_results
parse_openalex_next_cursor = _RESPONSE_MAPPER.extract_next_cursor


__all__ = [
    "parse_openalex_next_cursor",
    "parse_openalex_results",
]
