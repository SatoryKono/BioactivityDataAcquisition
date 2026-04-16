"""Shared builders for standard normalization profiles."""

from __future__ import annotations

from collections.abc import Callable, Collection, Mapping

from bioetl.domain.normalization.profiles.base import FieldRule, NormalizationProfile
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_abstract,
    normalize_profile_case,
    normalize_profile_date,
    normalize_profile_doi,
    normalize_profile_enum,
    normalize_profile_float,
    normalize_profile_int,
    normalize_profile_json_string,
    normalize_profile_null,
    normalize_profile_passthrough,
    normalize_profile_pmc_id,
    normalize_profile_pmid,
    normalize_profile_text,
    normalize_profile_title,
    normalize_profile_unit,
)

FieldNormalizer = Callable[[object], object]
RuleComponent = tuple[FieldNormalizer, str]
RuleComponentSpec = RuleComponent | tuple[FieldNormalizer] | FieldNormalizer
RuleFamilySpec = tuple[frozenset[str], FieldNormalizer, str]

__all__ = ["build_standard_profile"]


def _normalize_field_collections(*collections: Collection[str]) -> tuple[frozenset[str], ...]:
    """Normalize multiple field collections to frozensets."""
    return tuple(frozenset(collection) for collection in collections)

def _normalize_mapping_fields(
    enum_fields: Mapping[str, frozenset[str]] | None,
    case_fields: Mapping[str, frozenset[str] | None] | None,
) -> tuple[Mapping[str, frozenset[str]], Mapping[str, frozenset[str] | None]]:
    """Normalize mapping fields with default empty dicts."""
    return enum_fields or {}, case_fields or {}

def _normalize_special_rules(
    special_rules: Mapping[str, RuleComponentSpec] | None,
) -> Mapping[str, RuleComponent]:
    """Normalize and coerce special rules."""
    if special_rules is None:
        return {}
    return {
        field_name: _coerce_rule_component(field_name=field_name, component=component)
        for field_name, component in special_rules.items()
    }

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


def _coerce_rule_component(
    *,
    field_name: str,
    component: RuleComponentSpec,
) -> RuleComponent:
    """Normalize legacy custom-rule shapes to the canonical (normalizer, notes) form."""
    if callable(component):
        return _default_custom_rule_component(field_name=field_name, normalizer=component)
    if _is_explicit_rule_component(component):
        return component
    if _is_single_normalizer_rule_component(component):
        return _default_custom_rule_component(
            field_name=field_name,
            normalizer=component[0],
        )
    raise ValueError(
        "special_rules entries must be a callable or a "
        "(normalizer, notes) tuple; got invalid component "
        f"for field '{field_name}': {component!r}"
    )


def _default_custom_rule_component(
    *,
    field_name: str,
    normalizer: FieldNormalizer,
) -> RuleComponent:
    return (
        normalizer,
        f"Apply custom normalization rule for field '{field_name}'.",
    )


def _is_explicit_rule_component(component: RuleComponentSpec) -> bool:
    return (
        isinstance(component, tuple)
        and len(component) == 2
        and callable(component[0])
        and isinstance(component[1], str)
    )


def _is_single_normalizer_rule_component(component: RuleComponentSpec) -> bool:
    return (
        isinstance(component, tuple)
        and len(component) == 1
        and callable(component[0])
    )


def _handle_special_rules(field_name: str, special_rules: Mapping[str, RuleComponent]) -> RuleComponent | None:
    """Handle special rules for specific fields."""
    if field_name in special_rules:
        return special_rules[field_name]
    return None

def _handle_enum_fields(field_name: str, enum_fields: Mapping[str, frozenset[str]]) -> RuleComponent | None:
    """Handle enum field normalization."""
    if field_name in enum_fields:
        allowed_values = enum_fields[field_name]
        return (
            lambda value: normalize_profile_enum(value, allowed_values=allowed_values),
            f"Normalize enum field '{field_name}' against allowed values.",
        )
    return None

def _handle_case_fields(field_name: str, case_fields: Mapping[str, frozenset[str] | None]) -> RuleComponent | None:
    """Handle case field normalization."""
    if field_name in case_fields:
        allowed_values = case_fields[field_name]
        return (
            lambda value: normalize_profile_case(value, allowed_values=allowed_values),
            f"Normalize case for field '{field_name}'.",
        )
    return None

def _handle_unit_fields(field_name: str, unit_fields: frozenset[str]) -> RuleComponent | None:
    """Handle unit field normalization."""
    if field_name in unit_fields:
        return (
            normalize_profile_unit,
            f"Canonicalize units for field '{field_name}'.",
        )
    return None

def _handle_null_fields(field_name: str, null_fields: frozenset[str]) -> RuleComponent | None:
    """Handle null field normalization."""
    if field_name in null_fields:
        return (
            normalize_profile_null,
            f"Convert pseudo-null values to None for field '{field_name}'.",
        )
    return None


def _compose_null_aware_rule(
    *,
    base_rule: RuleComponent,
    field_name: str,
) -> RuleComponent:
    """Apply pseudo-null normalization before a field-specific normalizer."""
    base_normalizer, base_notes = base_rule

    def _normalize(value: object) -> object:
        null_normalized = normalize_profile_null(value)
        if null_normalized is None:
            return None
        return base_normalizer(null_normalized)

    return (
        _normalize,
        f"{base_notes} Pseudo-null values also collapse to None for field '{field_name}'.",
    )

def _handle_field_families(
    field_name: str,
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
) -> RuleComponent | None:
    """Handle field family specific rules."""
    for fields, normalizer, notes in _rule_family_specs(
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
    ):
        if field_name in fields:
            return normalizer, notes
    return None

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
    set_like_fields: frozenset[str],
    json_string_fields: frozenset[str],
    enum_fields: Mapping[str, frozenset[str]],
    case_fields: Mapping[str, frozenset[str] | None],
    unit_fields: frozenset[str],
    null_fields: frozenset[str],
    special_rules: Mapping[str, RuleComponent],
) -> RuleComponent:
    """Determine the appropriate rule component for a field."""
    base_rule: RuleComponent | None = None

    handlers = [
        lambda: _handle_special_rules(field_name, special_rules),
        lambda: _handle_enum_fields(field_name, enum_fields),
        lambda: _handle_case_fields(field_name, case_fields),
        lambda: _handle_unit_fields(field_name, unit_fields),
        lambda: _handle_field_families(
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
        ),
    ]

    for handler in handlers:
        result = handler()
        if result is not None:
            base_rule = result
            break

    if field_name in null_fields:
        if base_rule is None:
            null_rule = _handle_null_fields(field_name, null_fields)
            assert null_rule is not None
            return null_rule
        return _compose_null_aware_rule(
            base_rule=base_rule,
            field_name=field_name,
        )

    return base_rule or _DEFAULT_RULE_COMPONENT


_DEFAULT_RULE_COMPONENT: RuleComponent = (
    normalize_profile_text,
    "Trim and collapse blank textual values to None where applicable.",
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
    set_like_fields: frozenset[str],
    json_string_fields: frozenset[str],
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
        (
            set_like_fields,
            normalize_profile_json_string,
            "Canonicalize JSON; when represented as an array, treat item order as set-like for content_hash.",
        ),
        (
            json_string_fields,
            normalize_profile_json_string,
            "Canonicalize JSON-bearing string payloads after textual cleanup.",
        ),
    )
