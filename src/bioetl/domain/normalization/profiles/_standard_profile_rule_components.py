"""Rule-component helpers for the standard profile builder."""

from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from functools import cache

from bioetl.domain.normalization.profiles._standard_profile_rule_context import (
    _DEFAULT_RULE_COMPONENT,
    FieldNormalizer,
    RuleComponent,
    RuleComponentSpec,
    _build_rule_component_context,
    _handle_special_rules,
    _normalize_special_rules,
    _RuleComponentContext,
)
from bioetl.domain.normalization.profiles._standard_profile_rule_families import (
    RuleFamilyFieldSets,
    _rule_family_specs,
)
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_case,
    normalize_profile_enum,
    normalize_profile_null,
    normalize_profile_unit,
)

__all__ = [
    "RuleComponent",
    "RuleComponentSpec",
    "_build_rule_component_context",
    "_normalize_special_rules",
    "_rule_components",
]


@cache
def _normalizer_accepts_record_context(normalizer: FieldNormalizer) -> bool:
    try:
        parameters = tuple(inspect.signature(normalizer).parameters.values())
    except (TypeError, ValueError):
        return False
    return any(
        parameter.name == "record" or parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in parameters
    )


def _bound_enum_normalizer(allowed_values: frozenset[str]) -> FieldNormalizer:
    """Return a named enum normalizer with stable module/qualname identity."""
    values = frozenset(allowed_values)

    def normalize_bound_enum(value: object) -> object:
        return normalize_profile_enum(value, allowed_values=values)

    return normalize_bound_enum


def _bound_case_normalizer(
    allowed_values: frozenset[str] | None,
) -> FieldNormalizer:
    """Return a named case normalizer with stable module/qualname identity."""
    values = None if allowed_values is None else frozenset(allowed_values)

    def normalize_bound_case(value: object) -> object:
        return normalize_profile_case(value, allowed_values=values)

    return normalize_bound_case


def _handle_enum_fields(
    field_name: str, enum_fields: Mapping[str, frozenset[str]]
) -> RuleComponent | None:
    if field_name in enum_fields:
        allowed_values = enum_fields[field_name]
        return (
            _bound_enum_normalizer(allowed_values),
            (
                f"Normalize enum field '{field_name}' against allowed values, "
                "preserving canonical allowed-value casing and uppercase values "
                "when the registry defines uppercase enums."
            ),
        )
    return None


def _handle_case_fields(
    field_name: str, case_fields: Mapping[str, frozenset[str] | None]
) -> RuleComponent | None:
    if field_name in case_fields:
        allowed_values = case_fields[field_name]
        return (
            _bound_case_normalizer(allowed_values),
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

    def _normalize(
        value: object,
        record: Mapping[str, object] | None = None,
    ) -> object:
        null_normalized = normalize_profile_null(value)
        if record is not None and _normalizer_accepts_record_context(base_normalizer):
            return base_normalizer(null_normalized, record=record)
        if null_normalized is None:
            return None
        return base_normalizer(null_normalized)

    _normalize.__name__ = getattr(base_normalizer, "__name__", "_normalize")
    return (
        _normalize,
        f"{base_notes} Pseudo-null values also collapse to None for field '{field_name}'.",
    )


def _handle_field_families(
    field_name: str,
    field_sets: RuleFamilyFieldSets,
) -> RuleComponent | None:
    for fields, normalizer, notes in _rule_family_specs(field_sets=field_sets):
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
    handlers: tuple[Callable[[], RuleComponent | None], ...] = (
        lambda: _handle_special_rules(field_name, context.special_rules),
        lambda: _handle_enum_fields(field_name, context.enum_fields),
        lambda: _handle_case_fields(field_name, context.case_fields),
        lambda: _handle_unit_fields(field_name, context.unit_fields),
        lambda: _handle_field_families(
            field_name=field_name,
            field_sets=(
                context.title_fields,
                context.abstract_fields,
                context.doi_fields,
                context.pmid_fields,
                context.pmc_id_fields,
                context.date_fields,
                context.int_fields,
                context.float_fields,
                context.set_like_fields,
                context.json_string_fields,
                context.strict_json_fields,
                context.boolean_fields,
                context.flag_fields,
                context.operator_fields,
                context.ontology_id_fields,
            ),
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
