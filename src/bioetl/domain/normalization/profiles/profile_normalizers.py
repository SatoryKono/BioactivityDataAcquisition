"""Shared pure normalizers for normalization profiles."""

from __future__ import annotations

import math

from bioetl.domain.normalization.dates import normalize_partial_date
from bioetl.domain.normalization.identifiers import (
    normalize_doi,
    normalize_pmc_id,
    normalize_pmid,
)
from bioetl.domain.normalization.json import canonicalize_json_string
from bioetl.domain.normalization.rules import (
    normalize_case,
    normalize_null,
    normalize_unit,
)
from bioetl.domain.normalization.text import normalize_abstract as _normalize_abstract
from bioetl.domain.normalization.text import normalize_string
from bioetl.domain.normalization.text import normalize_title as _normalize_title
from bioetl.domain.value_objects import SMILES

__all__ = [
    "normalize_profile_abstract",
    "normalize_profile_canonical_smiles",
    "normalize_profile_case",
    "normalize_profile_date",
    "normalize_profile_doi",
    "normalize_profile_enum",
    "normalize_profile_float",
    "normalize_profile_int",
    "normalize_profile_isomeric_smiles",
    "normalize_profile_json_string",
    "normalize_profile_null",
    "normalize_profile_passthrough",
    "normalize_profile_pmc_id",
    "normalize_profile_pmid",
    "normalize_profile_smiles",
    "normalize_profile_text",
    "normalize_profile_title",
    "normalize_profile_unit",
]

_UNHANDLED = object()


def normalize_profile_null(value: object) -> object:
    """Convert pseudo-null values to proper None in profile fields.

    Args:
        value: The value to check for null patterns

    Returns:
        None if value matches null patterns, original value otherwise
    """
    return normalize_null(value)


def normalize_profile_passthrough(value: object) -> object:
    """Return one profile value unchanged."""
    return value


def normalize_profile_case(
    value: object, *, allowed_values: frozenset[str] | None = None
) -> object:
    """Normalize case for enum-like profile fields.

    Args:
        value: The value to normalize
        allowed_values: Optional set of allowed values for validation

    Returns:
        Normalized uppercase value if valid, None otherwise
    """
    return normalize_case(value, allowed_values)


def normalize_profile_unit(value: object) -> object:
    """Canonicalize unit strings in profile fields.

    Args:
        value: The unit value to normalize

    Returns:
        Canonical unit string or None if invalid
    """
    return normalize_unit(value)


def normalize_profile_enum(value: object, *, allowed_values: frozenset[str]) -> object:
    """Normalize one enum-like profile field against allowed values.

    Args:
        value: The value to normalize
        allowed_values: Frozenset of allowed enum values

    Returns:
        Normalized value if it's in allowed_values, None otherwise
    """
    if value is None:
        return None
    if isinstance(value, str):
        normalized = normalize_string(value)
        return normalized if normalized in allowed_values else None
    return value if value in allowed_values else None


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


def normalize_profile_int(value: object) -> object:
    """Coerce one integer-like value to stable scalar semantics."""
    if type(value) in {type(None), bool, int}:
        return value
    coerced = _coerce_profile_int(value)
    if coerced is _UNHANDLED:
        return value
    return coerced


def normalize_profile_float(value: object) -> object:
    """Coerce one float-like value to stable finite scalar semantics."""
    if type(value) in {type(None), bool}:
        return value
    return _normalize_profile_float_value(value)


def _normalize_profile_float_value(value: object) -> object:
    """Normalize already-eligible float-like values."""
    coerced = _coerce_profile_float(value)
    if coerced is _UNHANDLED:
        return value
    return _finalize_profile_float(coerced, fallback=value)


def _coerce_profile_int(value: object) -> int | str | float | None | object:
    """Return integer-like value, preserving non-integer floats and invalid text."""
    if isinstance(value, float):
        return int(value) if value.is_integer() else value
    if not isinstance(value, str):
        return _UNHANDLED
    return _coerce_profile_int_text(value)


def _coerce_profile_int_text(value: str) -> int | str | None:
    """Coerce normalized text to integer when possible."""
    normalized = normalize_string(value)
    if normalized is None:
        return None
    return _parse_profile_int_text(normalized)


def _parse_profile_int_text(value: str) -> int | str:
    """Parse integer text while preserving non-numeric payloads."""
    try:
        return int(value)
    except ValueError:
        return value


def _coerce_profile_float(value: object) -> float | str | None | object:
    """Return float-like value, preserving text that cannot be parsed."""
    if isinstance(value, int | float):
        return float(value)
    if not isinstance(value, str):
        return _UNHANDLED
    normalized = normalize_string(value)
    if normalized is None:
        return None
    try:
        return float(normalized)
    except ValueError:
        return normalized


def _finalize_profile_float(
    coerced: float | str | None | object,
    *,
    fallback: object,
) -> object:
    """Finalize coerced float-like values into stable persisted semantics."""
    if coerced is None or isinstance(coerced, str):
        return coerced
    if isinstance(coerced, float):
        return round(coerced, 10) if math.isfinite(coerced) else None
    return fallback


def normalize_profile_doi(value: object) -> object:
    """Normalize DOI-like profile values when the value is textual."""
    if not isinstance(value, str):
        return value
    return normalize_doi(value)


def normalize_profile_pmid(value: object) -> object:
    """Normalize PMID-like profile values with bool protection."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return normalize_pmid(value)
    if not isinstance(value, str):
        return value
    return _normalize_profile_pmid_text(value)


def _normalize_profile_pmid_text(value: str) -> str | None:
    """Normalize textual PMID payloads after generic string normalization."""
    normalized = normalize_string(value)
    if normalized is None:
        return None
    if normalized.lower().startswith("pmid:"):
        return normalize_pmid(normalized[5:])
    return normalize_pmid(normalized)


def normalize_profile_pmc_id(value: object) -> object:
    """Normalize PMC identifiers when the value is textual."""
    if not isinstance(value, str):
        return value
    return normalize_pmc_id(value)


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
