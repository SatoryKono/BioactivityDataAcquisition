"""Shared builders for standard normalization profiles."""

from __future__ import annotations

from collections.abc import Collection, Mapping

from bioetl.domain.normalization.profiles._standard_profile_rule_components import (
    RuleComponent,
    RuleComponentSpec,
    _normalize_special_rules,
    _rule_components,
)
from bioetl.domain.normalization.profiles.base import FieldRule, NormalizationProfile
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_passthrough,
)

__all__ = ["build_standard_profile"]


def _normalize_field_collections(
    *collections: Collection[str],
) -> tuple[frozenset[str], ...]:
    """Normalize multiple field collections to frozensets."""
    return tuple(frozenset(collection) for collection in collections)


def _normalize_mapping_fields(
    enum_fields: Mapping[str, frozenset[str]] | None,
    case_fields: Mapping[str, frozenset[str] | None] | None,
) -> tuple[Mapping[str, frozenset[str]], Mapping[str, frozenset[str] | None]]:
    """Normalize mapping fields with default empty dicts."""
    return enum_fields or {}, case_fields or {}


def _build_field_rules(
    schema_fields: Collection[str],
    normalized_meta_fields: frozenset[str],
    normalized_title_fields: frozenset[str],
    normalized_abstract_fields: frozenset[str],
    normalized_doi_fields: frozenset[str],
    normalized_pmid_fields: frozenset[str],
    normalized_pmc_id_fields: frozenset[str],
    normalized_date_fields: frozenset[str],
    normalized_int_fields: frozenset[str],
    normalized_float_fields: frozenset[str],
    normalized_set_like_fields: frozenset[str],
    normalized_json_string_fields: frozenset[str],
    normalized_enum_fields: Mapping[str, frozenset[str]],
    normalized_case_fields: Mapping[str, frozenset[str] | None],
    normalized_unit_fields: frozenset[str],
    normalized_null_fields: frozenset[str],
    normalized_special_rules: Mapping[str, RuleComponent],
) -> Mapping[str, RuleComponent]:
    """Build field rules for all schema fields."""
    return {
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
            json_string_fields=normalized_json_string_fields,
            enum_fields=normalized_enum_fields,
            case_fields=normalized_case_fields,
            unit_fields=normalized_unit_fields,
            null_fields=normalized_null_fields,
            special_rules=normalized_special_rules,
        )
        for field_name in schema_fields
    }


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
    json_string_fields: Collection[str] = (),
    enum_fields: Mapping[str, frozenset[str]] | None = None,
    case_fields: Mapping[str, frozenset[str] | None] | None = None,
    unit_fields: Collection[str] | None = None,
    null_fields: Collection[str] | None = None,
    special_rules: Mapping[str, RuleComponentSpec] | None = None,
) -> NormalizationProfile:
    """Build one field-complete normalization profile from common field families."""
    # Normalize all input collections
    (
        normalized_meta_fields,
        normalized_title_fields,
        normalized_abstract_fields,
        normalized_doi_fields,
        normalized_pmid_fields,
        normalized_pmc_id_fields,
        normalized_date_fields,
        normalized_int_fields,
        normalized_float_fields,
        normalized_set_like_fields,
        normalized_json_string_fields,
    ) = _normalize_field_collections(
        meta_fields,
        title_fields,
        abstract_fields,
        doi_fields,
        pmid_fields,
        pmc_id_fields,
        date_fields,
        int_fields,
        float_fields,
        set_like_fields,
        json_string_fields,
    )

    # Normalize mapping fields
    normalized_enum_fields, normalized_case_fields = _normalize_mapping_fields(
        enum_fields, case_fields
    )

    # Normalize special rules
    normalized_unit_fields = frozenset(unit_fields or ())
    normalized_null_fields = frozenset(null_fields or ())
    normalized_special_rules = _normalize_special_rules(special_rules)

    # Build field rules
    field_rules = _build_field_rules(
        schema_fields=schema_fields,
        normalized_meta_fields=normalized_meta_fields,
        normalized_title_fields=normalized_title_fields,
        normalized_abstract_fields=normalized_abstract_fields,
        normalized_doi_fields=normalized_doi_fields,
        normalized_pmid_fields=normalized_pmid_fields,
        normalized_pmc_id_fields=normalized_pmc_id_fields,
        normalized_date_fields=normalized_date_fields,
        normalized_int_fields=normalized_int_fields,
        normalized_float_fields=normalized_float_fields,
        normalized_set_like_fields=normalized_set_like_fields,
        normalized_json_string_fields=normalized_json_string_fields,
        normalized_enum_fields=normalized_enum_fields,
        normalized_case_fields=normalized_case_fields,
        normalized_unit_fields=normalized_unit_fields,
        normalized_null_fields=normalized_null_fields,
        normalized_special_rules=normalized_special_rules,
    )

    return NormalizationProfile(
        profile_name=profile_name,
        description=description,
        meta_fields=normalized_meta_fields,
        field_rules=field_rules,
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
    json_string_fields: frozenset[str],
    enum_fields: Mapping[str, frozenset[str]],
    case_fields: Mapping[str, frozenset[str] | None],
    unit_fields: frozenset[str],
    null_fields: frozenset[str],
    special_rules: Mapping[str, RuleComponent],
) -> FieldRule:
    include_in_hash = field_name not in meta_fields
    if field_name in meta_fields:
        notes = (
            "System/meta field is tracked by the normalization inventory and "
            "excluded from content_hash; persisted-row publication is defined "
            "separately by the Silver/Gold storage contract."
        )
        normalizer = normalize_profile_passthrough
    else:
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
            set_like_fields=set_like_fields,
            json_string_fields=json_string_fields,
            enum_fields=enum_fields,
            case_fields=case_fields,
            unit_fields=unit_fields,
            null_fields=null_fields,
            special_rules=special_rules,
        )
    return FieldRule(
        field_name=field_name,
        normalizer=normalizer,
        include_in_hash=include_in_hash,
        set_like=field_name in set_like_fields,
        notes=notes,
    )
