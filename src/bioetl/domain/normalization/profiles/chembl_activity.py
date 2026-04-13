"""Normalization profile for the ChEMBL Activity Silver schema."""

from __future__ import annotations

from collections.abc import Callable

from ._chembl_activity_fields import (
    CHEMBL_ACTIVITY_SCHEMA_FIELDS,
    FLOAT_FIELDS,
    INT_FIELDS,
    META_FIELDS,
    SET_LIKE_FIELDS,
    TEXT_FIELDS,
)
from .base import FieldRule, NormalizationProfile
from .profile_normalizers import (
    normalize_profile_doi,
    normalize_profile_float,
    normalize_profile_int,
    normalize_profile_json_string,
    normalize_profile_pmc_id,
    normalize_profile_pmid,
    normalize_profile_smiles,
    normalize_profile_text,
)

__all__ = [
    "CHEMBL_ACTIVITY_PROFILE",
    "CHEMBL_ACTIVITY_SCHEMA_FIELDS",
]

_SPECIAL_RULE_COMPONENTS: dict[str, tuple[Callable[[object], object], str]] = {
    "publication_doi": (
        normalize_profile_doi,
        "Normalize DOI to canonical registry form before hashing.",
    ),
    "publication_pmid": (
        normalize_profile_pmid,
        "Normalize PMID to digits-only canonical string.",
    ),
    "publication_pmc_id": (
        normalize_profile_pmc_id,
        "Normalize PMC identifier to canonical PMC-prefixed string.",
    ),
    "canonical_smiles": (
        lambda value: normalize_profile_smiles(value, is_canonical=True),
        "Normalize canonical SMILES via the domain SMILES Value Object; invalid values collapse to None.",
    ),
}


def _default_rule_components(field_name: str) -> tuple[Callable[[object], object], str]:
    if field_name in SET_LIKE_FIELDS:
        return (
            normalize_profile_json_string,
            "Canonicalize JSON; when represented as an array, treat item order as "
            "set-like for content_hash.",
        )
    if field_name in TEXT_FIELDS:
        return (
            normalize_profile_text,
            "Trim and collapse blank textual values to None where applicable.",
        )
    if field_name in INT_FIELDS:
        return (
            normalize_profile_int,
            "Coerce stable integer semantics for deterministic hashing.",
        )
    if field_name in FLOAT_FIELDS:
        return (
            normalize_profile_float,
            "Coerce stable float semantics and remove NaN/Inf noise.",
        )
    return normalize_profile_text, "Default textual normalization."


def _rule_components(field_name: str) -> tuple[Callable[[object], object], str]:
    special_rule = _SPECIAL_RULE_COMPONENTS.get(field_name)
    if special_rule is not None:
        return special_rule
    return _default_rule_components(field_name)


def _rule_for_field(field_name: str) -> FieldRule:
    include_in_hash = field_name not in META_FIELDS
    normalizer, notes = _rule_components(field_name)
    if field_name in META_FIELDS:
        notes = (
            "System/meta field is tracked by the normalization inventory and "
            "excluded from content_hash; persisted-row publication is defined "
            "separately by the Silver/Gold storage contract."
        )
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
