"""Pure canonicalizers for NCBI Taxonomy reference identifiers."""

from __future__ import annotations

from bioetl.domain.normalization._reference_id_support import (
    _NCBI_TAXONOMY_PREFIXES,
    _NCBI_TAXONOMY_RE,
    _normalized_text,
    _strip_prefixes,
)

__all__ = ["normalize_ncbi_taxonomy_reference_id"]


def _normalize_ncbi_taxonomy_text(value: str) -> int | None:
    candidate = _strip_prefixes(value, _NCBI_TAXONOMY_PREFIXES)
    if not _NCBI_TAXONOMY_RE.fullmatch(candidate):
        return None
    taxonomy_id = int(candidate)
    return taxonomy_id if taxonomy_id > 0 else None


def _normalize_positive_taxonomy_int(value: int) -> int | None:
    return value if value > 0 else None


def _normalize_ncbi_taxonomy_float(value: float) -> object:
    if not value.is_integer():
        return value
    normalized = _normalize_positive_taxonomy_int(int(value))
    return normalized if normalized is not None else value


def _normalize_ncbi_taxonomy_numeric(value: int | float) -> object | None:
    """Normalize numeric NCBI taxonomy representations when possible."""
    if isinstance(value, int):
        normalized = _normalize_positive_taxonomy_int(value)
        return normalized if normalized is not None else str(value)
    return _normalize_ncbi_taxonomy_float(value)


def _normalize_ncbi_taxonomy_textual(value: object) -> object:
    text = _normalized_text(value)
    if text is None:
        return value
    normalized = _normalize_ncbi_taxonomy_text(text)
    return normalized if normalized is not None else text


def normalize_ncbi_taxonomy_reference_id(value: object) -> object:
    """Normalize NCBI Taxonomy identifiers to positive integer scalar form."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return _normalize_ncbi_taxonomy_numeric(value)
    return _normalize_ncbi_taxonomy_textual(value)
