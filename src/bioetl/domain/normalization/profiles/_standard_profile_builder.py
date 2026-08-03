"""Shared builders for standard normalization profiles."""

from __future__ import annotations

from collections.abc import Collection, Mapping

from bioetl.domain.normalization.profiles._standard_profile_rule_components import (
    _build_rule_component_context,
    _normalize_special_rules,
    _rule_components,
)
from bioetl.domain.normalization.profiles._standard_profile_rule_context import (
    _RuleComponentContext,
)
from bioetl.domain.normalization.profiles._standard_profile_spec import (
    StandardProfileSpec,
    coerce_standard_profile_spec,
)
from bioetl.domain.normalization.profiles.base import FieldRule, NormalizationProfile
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_passthrough,
)

__all__ = ["StandardProfileSpec", "build_standard_profile"]


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
    normalized_set_like_fields: frozenset[str],
    normalized_hash_excluded_fields: frozenset[str],
    rule_context: _RuleComponentContext,
) -> Mapping[str, FieldRule]:
    """Build field rules for all schema fields."""
    field_rules: dict[str, FieldRule] = {}
    for field_name in schema_fields:
        field_rules[field_name] = _build_field_rule(
            field_name=field_name,
            meta_fields=normalized_meta_fields,
            set_like_fields=normalized_set_like_fields,
            hash_excluded_fields=normalized_hash_excluded_fields,
            rule_context=rule_context,
        )
    return field_rules


def build_standard_profile(
    spec: StandardProfileSpec | None = None,
    **overrides: object,
) -> NormalizationProfile:
    """Build one field-complete normalization profile from common field families."""
    profile_spec = coerce_standard_profile_spec(spec, overrides)
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
        normalized_hash_excluded_fields,
        normalized_json_string_fields,
        normalized_strict_json_fields,
        normalized_boolean_fields,
        normalized_flag_fields,
        normalized_operator_fields,
        normalized_ontology_id_fields,
    ) = _normalize_field_collections(
        profile_spec.meta_fields,
        profile_spec.title_fields,
        profile_spec.abstract_fields,
        profile_spec.doi_fields,
        profile_spec.pmid_fields,
        profile_spec.pmc_id_fields,
        profile_spec.date_fields,
        profile_spec.int_fields,
        profile_spec.float_fields,
        profile_spec.set_like_fields,
        profile_spec.hash_excluded_fields,
        profile_spec.json_string_fields,
        profile_spec.strict_json_fields,
        profile_spec.boolean_fields,
        profile_spec.flag_fields,
        profile_spec.operator_fields,
        profile_spec.ontology_id_fields,
    )

    # Normalize mapping fields
    normalized_enum_fields, normalized_case_fields = _normalize_mapping_fields(
        profile_spec.enum_fields, profile_spec.case_fields
    )

    # Normalize special rules
    normalized_unit_fields = frozenset(profile_spec.unit_fields or ())
    normalized_null_fields = frozenset(profile_spec.null_fields or ())
    normalized_special_rules = _normalize_special_rules(profile_spec.special_rules)
    rule_context = _build_rule_component_context(
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
        strict_json_fields=normalized_strict_json_fields,
        boolean_fields=normalized_boolean_fields,
        flag_fields=normalized_flag_fields,
        operator_fields=normalized_operator_fields,
        ontology_id_fields=normalized_ontology_id_fields,
        enum_fields=normalized_enum_fields,
        case_fields=normalized_case_fields,
        unit_fields=normalized_unit_fields,
        null_fields=normalized_null_fields,
        special_rules=normalized_special_rules,
    )

    # Build field rules
    field_rules = _build_field_rules(
        schema_fields=profile_spec.schema_fields,
        normalized_meta_fields=normalized_meta_fields,
        normalized_set_like_fields=normalized_set_like_fields,
        normalized_hash_excluded_fields=normalized_hash_excluded_fields,
        rule_context=rule_context,
    )

    return NormalizationProfile(
        profile_name=profile_spec.profile_name,
        description=profile_spec.description,
        meta_fields=normalized_meta_fields,
        field_aliases=profile_spec.field_aliases,
        field_rules=field_rules,
    )


def _build_field_rule(
    *,
    field_name: str,
    meta_fields: frozenset[str],
    set_like_fields: frozenset[str],
    hash_excluded_fields: frozenset[str],
    rule_context: _RuleComponentContext,
) -> FieldRule:
    include_in_hash = (
        field_name not in meta_fields and field_name not in hash_excluded_fields
    )
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
            context=rule_context,
        )
    return FieldRule(
        field_name=field_name,
        normalizer=normalizer,
        include_in_hash=include_in_hash,
        set_like=field_name in set_like_fields,
        notes=notes,
    )
