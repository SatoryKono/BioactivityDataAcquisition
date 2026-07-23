"""Context and special-rule coercion for standard profile rule components."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import cast

from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_text,
)

FieldNormalizer = Callable[..., object]
RuleComponent = tuple[FieldNormalizer, str]
RuleComponentSpec = RuleComponent | tuple[FieldNormalizer] | FieldNormalizer

_DEFAULT_RULE_COMPONENT: RuleComponent = (
    normalize_profile_text,
    "Trim and collapse blank textual values to None where applicable.",
)

__all__ = [
    "FieldNormalizer",
    "RuleComponent",
    "RuleComponentSpec",
    "_DEFAULT_RULE_COMPONENT",
    "_RuleComponentContext",
    "_build_rule_component_context",
    "_handle_special_rules",
    "_normalize_special_rules",
]


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
    strict_json_fields: frozenset[str]
    boolean_fields: frozenset[str]
    flag_fields: frozenset[str]
    operator_fields: frozenset[str]
    ontology_id_fields: frozenset[str]
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
        return cast(RuleComponent, component)
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
