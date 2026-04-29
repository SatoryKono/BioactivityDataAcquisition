"""Pure OpenAlex reference identifier helpers."""

from __future__ import annotations

from bioetl.domain.normalization._reference_id_support import (
    _OPENALEX_PREFIXES,
    _normalize_openalex_candidate,
    _normalized_text,
    _strip_prefixes,
)


def normalize_openalex_reference_id(value: object, *, prefix: str) -> object:
    """Normalize OpenAlex reference IDs from URLs or bare IDs."""
    text = _normalized_text(value)
    if text is None:
        return None if isinstance(value, str) or value is None else value
    candidate = _strip_prefixes(text, _OPENALEX_PREFIXES)
    return _normalize_openalex_candidate(candidate, prefix=prefix) or text


def normalize_openalex_author_reference_id(value: object) -> object:
    return normalize_openalex_reference_id(value, prefix="A")


def normalize_openalex_institution_reference_id(value: object) -> object:
    return normalize_openalex_reference_id(value, prefix="I")


def normalize_openalex_topic_reference_id(value: object) -> object:
    return normalize_openalex_reference_id(value, prefix="T")


def normalize_openalex_work_reference_id(value: object) -> object:
    return normalize_openalex_reference_id(value, prefix="W")
