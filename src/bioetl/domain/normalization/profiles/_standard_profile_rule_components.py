"""Rule-component helpers for the standard profile builder."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from bioetl.domain.normalization.profiles._standard_profile_rule_families import (
    _rule_family_specs,
)
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_case,
    normalize_profile_enum,
    normalize_profile_null,
    normalize_profile_text,
    normalize_profile_unit,
)

FieldNormalizer = Callable[[object], object]
RuleComponent = tuple[FieldNormalizer, str]
RuleComponentSpec = RuleComponent | tuple[FieldNormalizer] | FieldNormalizer

_DEFAULT_RULE_COMPONENT: RuleComponent = (
    normalize_profile_text,
    "Trim and collapse blank textual values to None where applicable.",
)


@dataclass(frozen=True, slots=True)
class _RuleComponentContext:
    title_fields: frozenset[str]
    abstract_fields: frozenset[str]
    doi_fields: frozenset[str]
    pmid_fields: frozenset[str]
    pmc_id_fields: frozenset[str]
    date_fields: frozenset[str]
    int_fields: frozenset[str]
    float_fields: frozenset[str]
    set_like_fields: frozenset[str]
    json_string_fields: frozenset[str]
    boolean_fields: frozenset[str]
    flag_fields: frozenset[str]
    operator_fields: frozenset[str]
    enum_fields: Mapping[str, frozenset[str]]
    case_fields: Mapping[str, frozenset[str] | None]
    unit_fields: frozenset[str]
    null_fields: frozenset[str]
    special_rules: Mapping[str, RuleComponent]


_build_rule_component_context = _RuleComponentContext


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


def _coerce_rule_component(
    *,
    field_name: str,
    component: RuleComponentSpec,
) -> RuleComponent:
    """Normalize legacy custom-rule shapes to the canonical (normalizer, notes) form."""
    if callable(component):
        return _default_custom_rule_component(
            field_name=field_name, normalizer=component
        )
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
        isinstance(component, tuple) and len(component) == 1 and callable(component[0])
    )


def _handle_special_rules(
    field_name: str, special_rules: Mapping[str, RuleComponent]
) -> RuleComponent | None:
    if field_name in special_rules:
        return special_rules[field_name]
    return None


def _handle_enum_fields(
    field_name: str, enum_fields: Mapping[str, frozenset[str]]
) -> RuleComponent | None:
    if field_name in enum_fields:
        allowed_values = enum_fields[field_name]
        return (
            lambda value: normalize_profile_enum(value, allowed_values=allowed_values),
            f"Normalize enum field '{field_name}' against allowed values.",
        )
    return None


def _handle_case_fields(
    field_name: str, case_fields: Mapping[str, frozenset[str] | None]
) -> RuleComponent | None:
    if field_name in case_fields:
        allowed_values = case_fields[field_name]
        return (
            lambda value: normalize_profile_case(value, allowed_values=allowed_values),
            f"Normalize case for field '{field_name}'.",
        )
    return None


def _handle_unit_fields(
    field_name: str, unit_fields: frozenset[str]
) -> RuleComponent | None:
    if field_name in unit_fields:
        return (
            normalize_profile_unit,
            f"Canonicalize units for field '{field_name}'.",
        )
    return None


def _handle_null_fields(
    field_name: str, null_fields: frozenset[str]
) -> RuleComponent | None:
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
    boolean_fields: frozenset[str],
    flag_fields: frozenset[str],
    operator_fields: frozenset[str],
) -> RuleComponent | None:
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
        boolean_fields=boolean_fields,
        flag_fields=flag_fields,
        operator_fields=operator_fields,
    ):
        if field_name in fields:
            return normalizer, notes
    return None


def _rule_components(
    *,
    field_name: str,
    context: _RuleComponentContext,
) -> RuleComponent:
    base_rule = _resolve_base_rule(
        field_name=field_name,
        context=context,
    )
    return _finalize_rule_component(
        field_name=field_name,
        base_rule=base_rule,
        null_fields=context.null_fields,
    )


def _resolve_base_rule(
    *,
    field_name: str,
    context: _RuleComponentContext,
) -> RuleComponent | None:
    handlers = (
        lambda: _handle_special_rules(field_name, context.special_rules),
        lambda: _handle_enum_fields(field_name, context.enum_fields),
        lambda: _handle_case_fields(field_name, context.case_fields),
        lambda: _handle_unit_fields(field_name, context.unit_fields),
        lambda: _handle_field_families(
            field_name=field_name,
            title_fields=context.title_fields,
            abstract_fields=context.abstract_fields,
            doi_fields=context.doi_fields,
            pmid_fields=context.pmid_fields,
            pmc_id_fields=context.pmc_id_fields,
            date_fields=context.date_fields,
            int_fields=context.int_fields,
            float_fields=context.float_fields,
            set_like_fields=context.set_like_fields,
            json_string_fields=context.json_string_fields,
            boolean_fields=context.boolean_fields,
            flag_fields=context.flag_fields,
            operator_fields=context.operator_fields,
        ),
    )
    for handler in handlers:
        result = handler()
        if result is not None:
            return result
    return None


def _finalize_rule_component(
    *,
    field_name: str,
    base_rule: RuleComponent | None,
    null_fields: frozenset[str],
) -> RuleComponent:
    if field_name not in null_fields:
        return base_rule or _DEFAULT_RULE_COMPONENT
    if base_rule is None:
        null_rule = _handle_null_fields(field_name, null_fields)
        assert null_rule is not None
        return null_rule
    return _compose_null_aware_rule(base_rule=base_rule, field_name=field_name)


__all__ = [
    "RuleComponent",
    "RuleComponentSpec",
    "_build_rule_component_context",
    "_normalize_special_rules",
    "_rule_components",
]
