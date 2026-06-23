"""Common DOI helper functions for adapter-side transport normalization."""

from __future__ import annotations

from bioetl.domain.normalization import strip_doi_prefix

__all__ = ["strip_doi_transport_prefix"]


def strip_doi_transport_prefix(
    doi: str,
    *,
    allow_uppercase_prefix: bool = False,  # kept for API compat; always strips DOI: now
) -> str:
    """Remove transport-style DOI prefixes while preserving the DOI payload.

    Delegates to :func:`bioetl.domain.normalization.strip_doi_prefix`.

    Args:
        doi: Raw DOI string that may contain URL-style or ``doi:`` prefixes.
        allow_uppercase_prefix: Deprecated — ``DOI:`` is now always stripped.

    Returns:
        DOI string with supported transport prefixes removed.
    """
    _ = allow_uppercase_prefix
    return str(strip_doi_prefix(doi))
