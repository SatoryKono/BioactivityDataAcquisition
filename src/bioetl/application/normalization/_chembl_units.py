"""URI parsing helpers for QUDT / legacy OpenPhacts unit identifiers.

Thin wrappers over the domain host/path normalizer so application/tests keep a
stable import path without duplicating URI authority parsing.
"""

from __future__ import annotations

from bioetl.domain.normalization._chembl_units import _uri_host_and_path

__all__ = [
    "_legacy_qudt_identifier_from_uri",
    "_qudt_identifier_from_uri",
]


def _qudt_identifier_from_uri(value: str) -> str | None:
    parsed = _uri_host_and_path(value)
    if parsed is None:
        return None
    hostname, path = parsed
    if hostname == "qudt.org" and path.startswith("/vocab/unit/"):
        return path.rsplit("/", maxsplit=1)[-1]
    return None


def _legacy_qudt_identifier_from_uri(value: str) -> str | None:
    parsed = _uri_host_and_path(value)
    if parsed is None:
        return None
    hostname, path = parsed
    if hostname == "www.openphacts.org" and path.casefold() == "/units/nanomolar":
        return "NanoMOL-PER-L"
    return None
