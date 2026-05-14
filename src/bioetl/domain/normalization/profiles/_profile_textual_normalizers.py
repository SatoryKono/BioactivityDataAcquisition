"""Private textual and identifier normalizers reused by profile facades."""

from __future__ import annotations

from bioetl.domain.normalization.json import deserialize_json_value
from bioetl.domain.normalization.dates import normalize_partial_date
from bioetl.domain.normalization.json import canonicalize_json_string, serialize_json_canonical
from bioetl.domain.normalization.reference_ids import (
    normalize_doi_reference_id,
    normalize_pmcid_reference_id,
    normalize_pmid_reference_id,
)
from bioetl.domain.normalization.text import normalize_abstract as _normalize_abstract
from bioetl.domain.normalization.text import normalize_string
from bioetl.domain.normalization.text import normalize_title as _normalize_title
from bioetl.domain.value_objects.chemical import SMILES


def normalize_profile_text(value: object) -> object:
    """Normalize one textual profile field when the value is a string."""
    if not isinstance(value, str):
        return value
    return normalize_string(value)


def normalize_profile_json_string(value: object) -> object:
    """Canonicalize one JSON-like string while preserving invalid payloads."""
    if not isinstance(value, str):
        return value
    normalized = normalize_string(value)
    if normalized is None:
        return None
    try:
        canonical = canonicalize_json_string(normalized)
    except ValueError:
        return normalized
    return canonical if canonical is not None else normalized


def normalize_profile_json_string_unordered_collection(value: object) -> object:
    """Canonicalize one JSON-like unordered collection into deterministic row order."""
    normalized = _normalize_unordered_json_collection(value)
    return value if normalized is _UNHANDLED else normalized


def normalize_profile_json_string_strict(value: object) -> object:
    """Canonicalize one JSON-like string and fail closed on malformed payloads."""
    if not isinstance(value, str):
        return value
    normalized = normalize_string(value)
    if normalized is None:
        return None
    try:
        return canonicalize_json_string(normalized)
    except ValueError:
        return None


def normalize_profile_title(value: object) -> object:
    """Normalize one title-like profile field."""
    if not isinstance(value, str):
        return value
    return _normalize_title(value)


def normalize_profile_abstract(value: object) -> object:
    """Normalize one abstract-like profile field."""
    if not isinstance(value, str):
        return value
    return _normalize_abstract(value)


def normalize_profile_date(value: object) -> object:
    """Normalize one date-like profile field to canonical partial-date semantics."""
    if not isinstance(value, str):
        return value
    return normalize_partial_date(value)


def normalize_profile_doi(value: object) -> object:
    """Normalize DOI-like profile values through the shared reference-ID policy."""
    return normalize_doi_reference_id(value)


def normalize_profile_pmid(value: object) -> object:
    """Normalize PMID-like profile values through the shared reference-ID policy."""
    return normalize_pmid_reference_id(value)


def normalize_profile_pmc_id(value: object) -> object:
    """Normalize PMC identifiers through the shared reference-ID policy."""
    return normalize_pmcid_reference_id(value)


def normalize_profile_smiles(value: object, *, is_canonical: bool) -> str | None:
    """Normalize one SMILES-like value using the domain value object."""
    if value is None or not isinstance(value, str):
        return None
    normalized = SMILES.from_raw(
        value,
        is_canonical=is_canonical,
        mode="soft",
    )
    return str(normalized) if normalized is not None else None


def normalize_profile_canonical_smiles(value: object) -> str | None:
    """Normalize one canonical-SMILES profile field."""
    return normalize_profile_smiles(value, is_canonical=True)


def normalize_profile_isomeric_smiles(value: object) -> str | None:
    """Normalize one isomeric-SMILES profile field."""
    return normalize_profile_smiles(value, is_canonical=False)


_UNHANDLED = object()


def _normalize_unordered_json_collection(value: object) -> object:
    if isinstance(value, str):
        normalized = normalize_string(value)
        if normalized is None:
            return None
        try:
            parsed = deserialize_json_value(normalized)
        except ValueError:
            return normalized
    elif isinstance(value, list | tuple | set | frozenset):
        parsed = list(value)
    else:
        return _UNHANDLED

    if not isinstance(parsed, list):
        return serialize_json_canonical(parsed) if isinstance(parsed, dict) else value

    return serialize_json_canonical(_sort_json_collection(parsed))


def _sort_json_collection(values: list[object]) -> list[object]:
    return sorted(values, key=lambda item: serialize_json_canonical({"value": item}))
