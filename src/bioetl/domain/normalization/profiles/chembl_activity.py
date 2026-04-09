"""Normalization profile for the ChEMBL Activity Silver schema."""

from __future__ import annotations

import math
from collections.abc import Callable

from bioetl.domain.normalization.identifiers import (
    normalize_doi,
    normalize_pmc_id,
    normalize_pmid,
)
from bioetl.domain.normalization.json import canonicalize_json_string
from bioetl.domain.normalization.text import normalize_string
from bioetl.domain.value_objects import SMILES

from ._chembl_activity_fields import (
    CHEMBL_ACTIVITY_SCHEMA_FIELDS,
    FLOAT_FIELDS,
    INT_FIELDS,
    META_FIELDS,
    SET_LIKE_FIELDS,
    TEXT_FIELDS,
)
from .base import FieldRule, NormalizationProfile

__all__ = [
    "CHEMBL_ACTIVITY_PROFILE",
    "CHEMBL_ACTIVITY_SCHEMA_FIELDS",
]

_NO_NORMALIZED_RESULT = object()


def _normalize_text(value: object) -> object:
    if not isinstance(value, str):
        return value
    return normalize_string(value)


def _normalize_json_string(value: object) -> object:
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


def _normalize_int_like(value: object) -> object:
    direct = _normalize_int_like_direct(value)
    if direct is not _NO_NORMALIZED_RESULT:
        return direct
    if not isinstance(value, str):
        return value
    return _normalize_int_like_string(value)


def _normalize_int_like_direct(value: object) -> object:
    if type(value) in {type(None), bool}:
        return value
    if type(value) is int:
        return value
    if not isinstance(value, float):
        return _NO_NORMALIZED_RESULT
    return _normalize_float_as_int_candidate(value)


def _normalize_float_as_int_candidate(value: float) -> object:
    if value.is_integer():
        return int(value)
    return value


def _normalize_int_like_string(value: str) -> object:
    normalized = normalize_string(value)
    if normalized is None:
        return None
    try:
        return int(normalized)
    except ValueError:
        return normalized


def _normalize_float_like(value: object) -> object:
    preserved = _preserve_nullable_scalar(value)
    if preserved is not _NO_NORMALIZED_RESULT:
        return preserved
    normalized = _coerce_float_like(value)
    return _finalize_float_like(value, normalized)


def _preserve_nullable_scalar(value: object) -> object:
    if type(value) in {type(None), bool}:
        return value
    return _NO_NORMALIZED_RESULT


def _finalize_float_like(original_value: object, normalized: object) -> object:
    if normalized is _NO_NORMALIZED_RESULT:
        return original_value
    if normalized is None:
        return None
    if isinstance(normalized, str):
        return normalized
    if isinstance(normalized, int | float):
        return _normalize_finite_float(float(normalized))
    return original_value


def _normalize_finite_float(value: float) -> float | None:
    if _is_non_finite_float(value):
        return None
    return round(value, 10)


def _is_non_finite_float(value: float) -> bool:
    return math.isnan(value) or math.isinf(value)


def _coerce_float_like(value: object) -> object:
    if isinstance(value, int | float):
        return float(value)
    if not isinstance(value, str):
        return _NO_NORMALIZED_RESULT
    stripped = normalize_string(value)
    if stripped is None:
        return None
    try:
        return float(stripped)
    except ValueError:
        return stripped


def _normalize_publication_doi(value: object) -> object:
    if not isinstance(value, str):
        return value
    return normalize_doi(value)


def _normalize_publication_pmid(value: object) -> object:
    if isinstance(value, bool):
        return None
    if not isinstance(value, str | int):
        return value
    return normalize_pmid(value)


def _normalize_publication_pmc_id(value: object) -> object:
    if not isinstance(value, str):
        return value
    return normalize_pmc_id(value)


def _normalize_smiles_value(value: object, *, is_canonical: bool) -> object:
    if value is None or not isinstance(value, str):
        return None
    normalized = SMILES.from_raw(
        value,
        is_canonical=is_canonical,
        mode="soft",
    )
    return str(normalized) if normalized is not None else None


_SPECIAL_RULE_COMPONENTS: dict[str, tuple[Callable[[object], object], str]] = {
    "publication_doi": (
        _normalize_publication_doi,
        "Normalize DOI to canonical registry form before hashing.",
    ),
    "publication_pmid": (
        _normalize_publication_pmid,
        "Normalize PMID to digits-only canonical string.",
    ),
    "publication_pmc_id": (
        _normalize_publication_pmc_id,
        "Normalize PMC identifier to canonical PMC-prefixed string.",
    ),
    "canonical_smiles": (
        lambda value: _normalize_smiles_value(value, is_canonical=True),
        "Normalize canonical SMILES via the domain SMILES Value Object; invalid values collapse to None.",
    ),
}


def _default_rule_components(field_name: str) -> tuple[Callable[[object], object], str]:
    if field_name in SET_LIKE_FIELDS:
        return (
            _normalize_json_string,
            "Canonicalize JSON; when represented as an array, treat item order as "
            "set-like for content_hash.",
        )
    if field_name in TEXT_FIELDS:
        return (
            _normalize_text,
            "Trim and collapse blank textual values to None where applicable.",
        )
    if field_name in INT_FIELDS:
        return (
            _normalize_int_like,
            "Coerce stable integer semantics for deterministic hashing.",
        )
    if field_name in FLOAT_FIELDS:
        return (
            _normalize_float_like,
            "Coerce stable float semantics and remove NaN/Inf noise.",
        )
    return _normalize_text, "Default textual normalization."


def _rule_components(field_name: str) -> tuple[Callable[[object], object], str]:
    special_rule = _SPECIAL_RULE_COMPONENTS.get(field_name)
    if special_rule is not None:
        return special_rule
    return _default_rule_components(field_name)


def _rule_for_field(field_name: str) -> FieldRule:
    include_in_hash = field_name not in META_FIELDS
    normalizer, notes = _rule_components(field_name)
    if field_name in META_FIELDS:
        notes = "System/meta field retained for storage but excluded from content_hash."
    return FieldRule(
        field_name=field_name,
        normalizer=normalizer,
        include_in_hash=include_in_hash,
        set_like=field_name in SET_LIKE_FIELDS,
        notes=notes,
    )


CHEMBL_ACTIVITY_PROFILE = NormalizationProfile(
    profile_name="chembl.activity",
    description=(
        "Canonical field-level normalization policy for the ChEMBL Activity Silver schema."
    ),
    meta_fields=META_FIELDS,
    field_rules={field_name: _rule_for_field(field_name) for field_name in CHEMBL_ACTIVITY_SCHEMA_FIELDS},
)

CHEMBL_ACTIVITY_PROFILE.assert_covers_schema(CHEMBL_ACTIVITY_SCHEMA_FIELDS)
