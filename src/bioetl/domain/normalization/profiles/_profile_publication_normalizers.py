"""Publication-oriented profile normalizers shared by schema profiles."""

from __future__ import annotations

from bioetl.domain.mapping.publication_type_mapping import normalize_publication_type
from bioetl.domain.normalization.text import normalize_string

__all__ = [
    "normalize_profile_publication_type",
    "normalize_profile_publication_type_raw",
    "normalize_profile_semantic_scholar_publication_type_raw",
]

_SEMANTIC_SCHOLAR_PUBLICATION_TYPE_CANONICAL = {
    value.casefold(): value
    for value in (
        "JournalArticle",
        "Conference",
        "CaseReport",
        "ClinicalTrial",
        "MetaAnalysis",
        "Dataset",
        "Book",
        "BookSection",
        "LettersAndComments",
        "News",
        "Study",
        "Review",
        "Editorial",
        "Letter",
        "Other",
    )
}


def normalize_profile_publication_type(
    value: object,
    *,
    allowed_values: frozenset[str],
) -> object:
    """Normalize publication type through the canonical mapping and enum gate."""
    if not isinstance(value, str):
        return None
    cleaned = normalize_string(value)
    if cleaned is None:
        return None
    normalized = normalize_publication_type(cleaned)
    if normalized is None:
        return None
    return normalized if normalized in allowed_values else None


def normalize_profile_publication_type_raw(value: object) -> object:
    """Normalize raw provider publication-type tokens without mapping to canonical taxonomy."""
    if not isinstance(value, str):
        return None
    cleaned = normalize_string(value)
    return cleaned.upper() if cleaned is not None else None


def normalize_profile_semantic_scholar_publication_type_raw(value: object) -> object:
    """Canonicalize known Semantic Scholar raw type spellings without closing the universe."""
    if not isinstance(value, str):
        return None
    cleaned = normalize_string(value)
    if cleaned is None:
        return None
    return _SEMANTIC_SCHOLAR_PUBLICATION_TYPE_CANONICAL.get(
        cleaned.casefold(),
        cleaned,
    )
