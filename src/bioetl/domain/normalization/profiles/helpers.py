"""Shared pure helpers for normalization profiles."""

from __future__ import annotations

import math

from bioetl.domain.normalization.identifiers import (
    normalize_doi,
    normalize_pmc_id,
    normalize_pmid,
)
from bioetl.domain.normalization.json import canonicalize_json_string
from bioetl.domain.normalization.text import normalize_string
from bioetl.domain.value_objects import SMILES

__all__ = [
    "normalize_profile_doi",
    "normalize_profile_float",
    "normalize_profile_int",
    "normalize_profile_json_string",
    "normalize_profile_pmc_id",
    "normalize_profile_pmid",
    "normalize_profile_smiles",
    "normalize_profile_text",
]

_UNHANDLED = object()


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


def normalize_profile_int(value: object) -> object:
    """Coerce one integer-like value to stable scalar semantics."""
    if type(value) in {type(None), bool}:
        return value
    if type(value) is int:
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else value
    if not isinstance(value, str):
        return value
    normalized = normalize_string(value)
    if normalized is None:
        return None
    try:
        return int(normalized)
    except ValueError:
        return normalized


def normalize_profile_float(value: object) -> object:
    """Coerce one float-like value to stable finite scalar semantics."""
    if type(value) in {type(None), bool}:
        return value
    coerced = _coerce_profile_float(value)
    if coerced is _UNHANDLED:
        return value
    if coerced is None:
        return None
    if isinstance(coerced, str):
        return coerced
    return round(coerced, 10) if math.isfinite(coerced) else None


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


def normalize_profile_doi(value: object) -> object:
    """Normalize DOI-like profile values when the value is textual."""
    if not isinstance(value, str):
        return value
    return normalize_doi(value)


def normalize_profile_pmid(value: object) -> object:
    """Normalize PMID-like profile values with bool protection."""
    if isinstance(value, bool):
        return None
    if not isinstance(value, str | int):
        return value
    return normalize_pmid(value)


def normalize_profile_pmc_id(value: object) -> object:
    """Normalize PMC identifiers when the value is textual."""
    if not isinstance(value, str):
        return value
    return normalize_pmc_id(value)


def normalize_profile_smiles(value: object, *, is_canonical: bool) -> object:
    """Normalize one SMILES-like value using the domain value object."""
    if value is None or not isinstance(value, str):
        return None
    normalized = SMILES.from_raw(
        value,
        is_canonical=is_canonical,
        mode="soft",
    )
    return str(normalized) if normalized is not None else None
