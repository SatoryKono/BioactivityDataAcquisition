"""Publication-oriented profile normalizers shared by schema profiles."""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.domain.mapping.publication_type_classification import (
    build_publication_type_classification_payload,
    normalize_publication_classification_field,
)
from bioetl.domain.mapping.publication_type_mapping import normalize_publication_type
from bioetl.domain.normalization.text import normalize_string

__all__ = [
    "normalize_profile_chembl_publication_classification_field",
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


def _publication_type_source_value(
    value: object,
    *,
    record: Mapping[str, object] | None = None,
) -> str | None:
    if record is not None:
        raw_field_value = record.get("publication_type_raw")
        if isinstance(raw_field_value, str):
            cleaned_raw = normalize_string(raw_field_value)
            if cleaned_raw is not None:
                return cleaned_raw
    if not isinstance(value, str):
        return None
    return normalize_string(value)


def normalize_profile_publication_type(
    value: object,
    *,
    allowed_values: frozenset[str],
    record: Mapping[str, object] | None = None,
) -> object:
    """Normalize publication type through the canonical mapping and enum gate."""
    cleaned = _publication_type_source_value(value, record=record)
    if cleaned is None:
        return None
    normalized = normalize_publication_type(cleaned)
    if normalized is None:
        return None
    return normalized if normalized in allowed_values else None


def normalize_profile_chembl_publication_classification_field(
    value: object,
    *,
    field_name: str,
    record: Mapping[str, object] | None = None,
) -> object:
    """Derive one ChEMBL publication classification field from raw provider type."""
    payload = _chembl_publication_classification_payload(record)
    if payload is not None:
        derived = payload.get(field_name)
        return normalize_publication_classification_field(field_name, derived)
    return normalize_publication_classification_field(field_name, value)


def _chembl_publication_classification_payload(
    record: Mapping[str, object] | None,
) -> Mapping[str, object] | None:
    source_value = _publication_type_source_value(None, record=record)
    if source_value is None:
        return None
    try:
        return build_publication_type_classification_payload(
            "chembl",
            raw_type=source_value,
        )
    except RuntimeError:
        return None


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
