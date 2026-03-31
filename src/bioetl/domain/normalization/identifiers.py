"""Pure identifier normalization helpers."""

from __future__ import annotations

__all__ = [
    "normalize_doi",
    "normalize_pmc_id",
    "normalize_pmid",
    "strip_doi_prefix",
]

_DOI_URL_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "doi:",
    "DOI:",
)


def strip_doi_prefix(doi: str) -> str:
    """Strip known DOI URL/scheme prefixes, preserving the DOI payload."""
    for prefix in _DOI_URL_PREFIXES:
        if doi.startswith(prefix):
            return doi[len(prefix) :]
    return doi


def normalize_doi(doi: str | None) -> str | None:
    """Normalize DOI to lowercase bare form."""
    if not doi:
        return None
    stripped = strip_doi_prefix(doi).strip().lower()
    return stripped if stripped else None


def _normalize_pmid_from_int(pmid: int) -> str | None:
    """Normalize integer PMID input."""
    return str(pmid) if pmid > 0 else None


def _normalize_pmid_from_str(pmid: str) -> str | None:
    """Normalize string PMID input."""
    value = pmid.strip()
    if not value or not value.isdigit():
        return None

    normalized = str(int(value))
    return normalized if normalized != "0" else None


def normalize_pmid(pmid: str | int | None) -> str | None:
    """Normalize PubMed ID to canonical digits-only string."""
    if pmid is None or isinstance(pmid, bool):
        return None

    if isinstance(pmid, int):
        return _normalize_pmid_from_int(pmid)

    if isinstance(pmid, str):
        return _normalize_pmid_from_str(pmid)

    return None


def normalize_pmc_id(pmc_id: str | None) -> str | None:
    """Normalize PMC ID to uppercase with ``PMC`` prefix."""
    if not pmc_id:
        return None
    stripped = pmc_id.strip()
    if not stripped:
        return None
    if not stripped.upper().startswith("PMC"):
        return f"PMC{stripped}"
    return stripped.upper()
