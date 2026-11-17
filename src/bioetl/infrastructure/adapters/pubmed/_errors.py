"""Shared PubMed adapter exception groups."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.infrastructure.adapters.common.error_bundles import (
    build_common_network_error_bundle,
)

__all__ = ["PUBMED_COMMON_ERRORS", "PUBMED_RECORD_ERRORS"]

PUBMED_COMMON_ERRORS: tuple[type[Exception], ...] = build_common_network_error_bundle()

PUBMED_RECORD_ERRORS: tuple[type[Exception], ...] = (*PUBMED_COMMON_ERRORS, KeyError)


class PubMedSearchPayloadError(Exception):
    """ESearch JSON is not a result object and must not look like no hits."""


def parse_esearch_payload(payload: object) -> tuple[list[str], int | None]:
    """Read ``idlist`` and numeric ``count`` from an ESearch JSON object."""
    if not isinstance(payload, Mapping):
        raise PubMedSearchPayloadError("ESearch payload is not an object")
    if "esearchresult" not in payload:
        return [], None
    result = payload["esearchresult"]
    if not isinstance(result, Mapping):
        raise PubMedSearchPayloadError("ESearch esearchresult is not an object")
    return (
        require_esearch_idlist(result),
        coerce_esearch_count(result.get("count")),
    )


def require_esearch_idlist(result: Mapping[str, object]) -> list[str]:
    """Return PMID strings, or an empty list when ``idlist`` is absent."""
    if "idlist" not in result:
        return []
    raw_ids = result["idlist"]
    if not isinstance(raw_ids, list):
        raise PubMedSearchPayloadError("ESearch idlist is not a list")
    return [str(item) for item in raw_ids if item is not None]


def coerce_esearch_count(value: object) -> int | None:
    """Accept the integer ``count`` NCBI sends as a number or a decimal string."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return None
