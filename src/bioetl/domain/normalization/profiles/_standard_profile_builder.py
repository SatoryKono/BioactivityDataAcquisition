"""Shared builders for standard normalization profiles."""

from __future__ import annotations

from collections.abc import Callable, Collection, Mapping

from bioetl.domain.normalization.profiles.base import FieldRule, NormalizationProfile
from bioetl.domain.normalization.profiles.helpers import (
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
RuleFamilySpec = tuple[frozenset[str], FieldNormalizer, str]

__all__ = ["build_standard_profile"]


def build_standard_profile(
    *,
    profile_name: str,
    description: str,
    schema_fields: Collection[str],
    meta_fields: Collection[str],
    title_fields: Collection[str] = (),
    abstract_fields: Collection[str] = (),
    doi_fields: Collection[str] = (),
    pmid_fields: Collection[str] = (),
    pmc_id_fields: Collection[str] = (),
    date_fields: Collection[str] = (),
    int_fields: Collection[str] = (),
    float_fields: Collection[str] = (),
    set_like_fields: Collection[str] = (),
    special_rules: Mapping[str, RuleComponent] | None = None,
) -> NormalizationProfile:
    """Build one field-complete normalization profile from common field families."""
    normalized_meta_fields = frozenset(meta_fields)
    normalized_title_fields = frozenset(title_fields)
    normalized_abstract_fields = frozenset(abstract_fields)
    normalized_doi_fields = frozenset(doi_fields)
    normalized_pmid_fields = frozenset(pmid_fields)
    normalized_pmc_id_fields = frozenset(pmc_id_fields)
    normalized_date_fields = frozenset(date_fields)
    normalized_int_fields = frozenset(int_fields)
    normalized_float_fields = frozenset(float_fields)
    normalized_set_like_fields = frozenset(set_like_fields)
    normalized_special_rules = dict(special_rules or {})

    return NormalizationProfile(
        profile_name=profile_name,
        description=description,
        meta_fields=normalized_meta_fields,
        field_rules={
            field_name: _build_field_rule(
                field_name=field_name,
                meta_fields=normalized_meta_fields,
                title_fields=normalized_title_fields,
                abstract_fields=normalized_abstract_fields,
                doi_fields=normalized_doi_fields,
                pmid_fields=normalized_pmid_fields,
                pmc_id_fields=normalized_pmc_id_fields,
                date_fields=normalized_date_fields,
                int_fields=normalized_int_fields,
                float_fields=normalized_float_fields,
                set_like_fields=normalized_set_like_fields,
                special_rules=normalized_special_rules,
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
    for fields, normalizer, notes in _rule_family_specs(
        title_fields=title_fields,
        abstract_fields=abstract_fields,
        doi_fields=doi_fields,
        pmid_fields=pmid_fields,
        pmc_id_fields=pmc_id_fields,
        date_fields=date_fields,
        int_fields=int_fields,
        float_fields=float_fields,
    ):
        if field_name in fields:
            return normalizer, notes
    return _DEFAULT_RULE_COMPONENT


_DEFAULT_RULE_COMPONENT: RuleComponent = (
    normalize_profile_json_string,
    "Trim string values and canonicalize JSON-like string payloads when present.",
)


def _rule_family_specs(
    *,
    title_fields: frozenset[str],
    abstract_fields: frozenset[str],
    doi_fields: frozenset[str],
    pmid_fields: frozenset[str],
    pmc_id_fields: frozenset[str],
    date_fields: frozenset[str],
    int_fields: frozenset[str],
    float_fields: frozenset[str],
) -> tuple[RuleFamilySpec, ...]:
    """Return ordered field-family rules used by the standard profile builder."""
    return (
        (
            title_fields,
            normalize_profile_title,
            "Normalize title text to canonical textual form.",
        ),
        (
            abstract_fields,
            normalize_profile_abstract,
            "Normalize abstract text through canonical whitespace and entity cleanup.",
        ),
        (
            doi_fields,
            normalize_profile_doi,
            "Normalize DOI to canonical registry form before hashing.",
        ),
        (
            pmid_fields,
            normalize_profile_pmid,
            "Normalize PMID to digits-only canonical string.",
        ),
        (
            pmc_id_fields,
            normalize_profile_pmc_id,
            "Normalize PMC identifier to canonical PMC-prefixed string.",
        ),
        (
            date_fields,
            normalize_profile_date,
            "Canonicalize partial-date text to stable date semantics.",
        ),
        (
            int_fields,
            normalize_profile_int,
            "Coerce stable integer semantics for deterministic hashing.",
        ),
        (
            float_fields,
            normalize_profile_float,
            "Coerce stable float semantics and remove NaN/Inf noise.",
        ),
    )
