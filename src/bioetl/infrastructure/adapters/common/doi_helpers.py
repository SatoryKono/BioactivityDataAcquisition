"""Common DOI helper functions for adapter-side transport normalization."""

from __future__ import annotations

__all__ = ["strip_doi_transport_prefix"]


def strip_doi_transport_prefix(
    doi: str,
    *,
    allow_uppercase_prefix: bool = False,
) -> str:
    """Remove transport-style DOI prefixes while preserving the DOI payload.

    Args:
        doi: Raw DOI string that may contain URL-style or ``doi:`` prefixes.
        allow_uppercase_prefix: When True, also strips ``DOI:``.

    Returns:
        DOI string with supported transport prefixes removed.
    """
    if doi.startswith("https://doi.org/"):
        return doi[16:]
    if doi.startswith("http://doi.org/"):
        return doi[15:]
    if doi.startswith("doi:"):
        return doi[4:]
    if allow_uppercase_prefix and doi.startswith("DOI:"):
        return doi[4:]
    return doi
