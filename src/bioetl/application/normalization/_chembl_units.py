"""URI parsing helpers for QUDT / legacy OpenPhacts unit identifiers.

Application-owned copy keeps ChEMBL URI matrix-parameter semantics without a
cross-owner import of the domain private normalizer module.
"""

from __future__ import annotations

__all__ = [
    "_legacy_qudt_identifier_from_uri",
    "_qudt_identifier_from_uri",
]


def _uri_host_and_path(value: str) -> tuple[str, str] | None:
    """Extract a simple HTTP(S) host and path without urllib edge cases."""
    candidate = value.strip()
    scheme, separator, remainder = candidate.partition("://")
    if not separator or scheme.casefold() not in {"http", "https"}:
        return None
    # Strip query/fragment before authority/path split so `/` inside query
    # cannot be treated as a path (e.g. `?ref=/vocab/unit/...`).
    remainder = remainder.split("?", maxsplit=1)[0].split("#", maxsplit=1)[0]
    authority, slash, suffix = remainder.partition("/")
    authority = authority.rsplit("@", maxsplit=1)[-1].casefold()
    host = authority.split(":", maxsplit=1)[0]
    path = f"/{suffix}" if slash else ""
    path_prefix, path_separator, last_segment = path.rpartition("/")
    path = (
        f"{path_prefix}/{last_segment.partition(';')[0]}"
        if path_separator
        else path.partition(";")[0]
    )
    return host, path


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
