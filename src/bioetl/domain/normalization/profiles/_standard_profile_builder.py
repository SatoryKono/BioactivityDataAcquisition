"""Shared builders for standard profile modules."""

from __future__ import annotations

from collections.abc import Callable, Collection, Mapping

from .base import FieldRule, NormalizationProfile
from .helpers import (
    normalize_profile_abstract,
    normalize_profile_date,
    normalize_profile_doi,
    normalize_profile_float,
    normalize_profile_int,
    normalize_profile_json_string,
    normalize_profile_pmc_id,
    normalize_profile_pmid,
    normalize_profile_title,
)

FieldNormalizer = Callable[[object], object]
RuleComponent = tuple[FieldNormalizer, str]

__all__ = [
    "build_standard_profile",
]


def build_standard_profile(
    *,
    profile_name: str,
    description: str,
    schema_fields: Collection[str],
    meta_fields: frozenset[str],
    title_fields: frozenset[str] = frozenset(),
    abstract_fields: frozenset[str] = frozenset(),
    doi_fields: frozenset[str] = frozenset(),
    pmid_fields: frozenset[str] = frozenset(),
    pmc_id_fields: frozenset[str] = frozenset(),
    date_fields: frozenset[str] = frozenset(),
    int_fields: frozenset[str] = frozenset(),
    float_fields: frozenset[str] = frozenset(),
    set_like_fields: frozenset[str] = frozenset(),
    special_rules: Mapping[str, RuleComponent] | None = None,
) -> NormalizationProfile:
    """Build one standard profile from field-family declarations."""
    return NormalizationProfile(
        profile_name=profile_name,
        description=description,
        meta_fields=meta_fields,
        field_rules={
            field_name: _build_field_rule(
                field_name=field_name,
                meta_fields=meta_fields,
                title_fields=title_fields,
                abstract_fields=abstract_fields,
                doi_fields=doi_fields,
                pmid_fields=pmid_fields,
                pmc_id_fields=pmc_id_fields,
                date_fields=date_fields,
                int_fields=int_fields,
                float_fields=float_fields,
                set_like_fields=set_like_fields,
                special_rules=special_rules or {},
            )
            for field_name in schema_fields
        },
    )


def _build_field_rule(
    *,
    field_name: str,
    meta_fields: frozenset[str],
    title_fields: frozenset[str],
    abstract_fields: frozenset[str],
    doi_fields: frozenset[str],
    pmid_fields: frozenset[str],
    pmc_id_fields: frozenset[str],
    date_fields: frozenset[str],
    int_fields: frozenset[str],
    float_fields: frozenset[str],
    set_like_fields: frozenset[str],
    special_rules: Mapping[str, RuleComponent],
) -> FieldRule:
    include_in_hash = field_name not in meta_fields
    normalizer, notes = _rule_components(
        field_name=field_name,
        title_fields=title_fields,
        abstract_fields=abstract_fields,
        doi_fields=doi_fields,
        pmid_fields=pmid_fields,
        pmc_id_fields=pmc_id_fields,
        date_fields=date_fields,
        int_fields=int_fields,
        float_fields=float_fields,
        special_rules=special_rules,
    )
    if field_name in meta_fields:
        notes = "System/meta field retained for storage but excluded from content_hash."
    return FieldRule(
        field_name=field_name,
        normalizer=normalizer,
        include_in_hash=include_in_hash,
        set_like=field_name in set_like_fields,
        notes=notes,
    )


def _rule_components(
    *,
    field_name: str,
    title_fields: frozenset[str],
    abstract_fields: frozenset[str],
    doi_fields: frozenset[str],
    pmid_fields: frozenset[str],
    pmc_id_fields: frozenset[str],
    date_fields: frozenset[str],
    int_fields: frozenset[str],
    float_fields: frozenset[str],
    special_rules: Mapping[str, RuleComponent],
) -> RuleComponent:
    if field_name in special_rules:
        return special_rules[field_name]
    if field_name in title_fields:
        return (
            normalize_profile_title,
            "Normalize title text through deterministic text cleanup.",
        )
    if field_name in abstract_fields:
        return (
            normalize_profile_abstract,
            "Normalize abstract text through deterministic text cleanup.",
        )
    if field_name in doi_fields:
        return (
            normalize_profile_doi,
            "Normalize DOI to canonical registry form before hashing.",
        )
    if field_name in pmid_fields:
        return (
            normalize_profile_pmid,
            "Normalize PMID to canonical digits-only string.",
        )
    if field_name in pmc_id_fields:
        return (
            normalize_profile_pmc_id,
            "Normalize PMC identifier to canonical PMC-prefixed string.",
        )
    if field_name in date_fields:
        return (
            normalize_profile_date,
            "Normalize partial dates to canonical end-of-period ISO representation.",
        )
    if field_name in int_fields:
        return (
            normalize_profile_int,
            "Coerce stable integer semantics for deterministic hashing.",
        )
    if field_name in float_fields:
        return (
            normalize_profile_float,
            "Coerce stable float semantics and remove NaN/Inf noise.",
        )
    return (
        normalize_profile_json_string,
        "Trim string values and canonicalize JSON-like string payloads when present.",
    )
