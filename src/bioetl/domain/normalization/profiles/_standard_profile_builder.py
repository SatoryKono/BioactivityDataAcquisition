"""Shared builders for standard normalization profiles."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass, field, fields

from bioetl.domain.normalization.profiles._standard_profile_rule_components import (
    RuleComponent,
    RuleComponentSpec,
    _build_rule_component_context,
    _normalize_special_rules,
    _rule_components,
)
from bioetl.domain.normalization.profiles.base import FieldRule, NormalizationProfile
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_passthrough,
)

__all__ = ["StandardProfileSpec", "build_standard_profile"]


@dataclass(frozen=True, slots=True)
class StandardProfileSpec:
    """Typed input bundle for ``build_standard_profile``."""

    profile_name: str
    description: str
    schema_fields: Collection[str]
    meta_fields: Collection[str]
    title_fields: Collection[str] = field(default_factory=tuple)
    abstract_fields: Collection[str] = field(default_factory=tuple)
    doi_fields: Collection[str] = field(default_factory=tuple)
    pmid_fields: Collection[str] = field(default_factory=tuple)
    pmc_id_fields: Collection[str] = field(default_factory=tuple)
    date_fields: Collection[str] = field(default_factory=tuple)
    int_fields: Collection[str] = field(default_factory=tuple)
    float_fields: Collection[str] = field(default_factory=tuple)
    set_like_fields: Collection[str] = field(default_factory=tuple)
    json_string_fields: Collection[str] = field(default_factory=tuple)
    strict_json_fields: Collection[str] = field(default_factory=tuple)
    boolean_fields: Collection[str] = field(default_factory=tuple)
    flag_fields: Collection[str] = field(default_factory=tuple)
    operator_fields: Collection[str] = field(default_factory=tuple)
    ontology_id_fields: Collection[str] = field(default_factory=tuple)
    enum_fields: Mapping[str, frozenset[str]] | None = None
    case_fields: Mapping[str, frozenset[str] | None] | None = None
    unit_fields: Collection[str] | None = None
    null_fields: Collection[str] | None = None
    special_rules: Mapping[str, RuleComponentSpec] | None = None


_STANDARD_PROFILE_REQUIRED_FIELDS = (
    "profile_name",
    "description",
    "schema_fields",
    "meta_fields",
)
_STANDARD_PROFILE_OPTIONAL_DEFAULTS: dict[str, object] = {
    "title_fields": (),
    "abstract_fields": (),
    "doi_fields": (),
    "pmid_fields": (),
    "pmc_id_fields": (),
    "date_fields": (),
    "int_fields": (),
    "float_fields": (),
    "set_like_fields": (),
    "json_string_fields": (),
    "strict_json_fields": (),
    "boolean_fields": (),
    "flag_fields": (),
    "operator_fields": (),
    "ontology_id_fields": (),
    "enum_fields": None,
    "case_fields": None,
    "unit_fields": None,
    "null_fields": None,
    "special_rules": None,
}


def _resolve_standard_profile_value(
    *,
    field_name: str,
    spec: StandardProfileSpec | None,
    overrides: dict[str, object],
) -> object:
    if field_name in overrides:
        return overrides[field_name]
    if field_name in _STANDARD_PROFILE_OPTIONAL_DEFAULTS and spec is None:
        return _STANDARD_PROFILE_OPTIONAL_DEFAULTS[field_name]
    if spec is None:
        raise TypeError(
            f"build_standard_profile() missing required argument: '{field_name}'"
        )
    return getattr(spec, field_name)


def _coerce_standard_profile_spec(
    spec: StandardProfileSpec | None,
    overrides: dict[str, object],
) -> StandardProfileSpec:
    _ensure_required_standard_profile_fields(spec, overrides)
    return StandardProfileSpec(**_build_standard_profile_payload(spec, overrides))


def _ensure_required_standard_profile_fields(
    spec: StandardProfileSpec | None,
    overrides: dict[str, object],
) -> None:
    for field_name in _STANDARD_PROFILE_REQUIRED_FIELDS:
        _resolve_standard_profile_value(
            field_name=field_name,
            spec=spec,
            overrides=overrides,
        )


def _build_standard_profile_payload(
    spec: StandardProfileSpec | None,
    overrides: dict[str, object],
) -> dict[str, object]:
    payload: dict[str, object] = {}
    for field_info in fields(StandardProfileSpec):
        payload[field_info.name] = _resolve_standard_profile_value(
            field_name=field_info.name,
            spec=spec,
            overrides=overrides,
        )
    return payload


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
    rule_context: object,
) -> Mapping[str, RuleComponent]:
    """Build field rules for all schema fields."""
    return {
        field_name: _build_field_rule(
            field_name=field_name,
            meta_fields=normalized_meta_fields,
            set_like_fields=normalized_set_like_fields,
            rule_context=rule_context,
        )
        for field_name in schema_fields
    }


def build_standard_profile(
    spec: StandardProfileSpec | None = None,
    **overrides: object,
) -> NormalizationProfile:
    """Build one field-complete normalization profile from common field families."""
    profile_spec = _coerce_standard_profile_spec(spec, overrides)
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
        rule_context=rule_context,
    )

    return NormalizationProfile(
        profile_name=profile_spec.profile_name,
        description=profile_spec.description,
        meta_fields=normalized_meta_fields,
        field_rules=field_rules,
    )


def _build_field_rule(
    *,
    field_name: str,
    meta_fields: frozenset[str],
    set_like_fields: frozenset[str],
    rule_context: object,
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
            context=rule_context,
        )
    return FieldRule(
        field_name=field_name,
        normalizer=normalizer,
        include_in_hash=include_in_hash,
        set_like=field_name in set_like_fields,
        notes=notes,
    )
