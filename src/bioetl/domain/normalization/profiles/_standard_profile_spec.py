"""Typed spec and coercion helpers for standard normalization profiles."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass, field, fields
from typing import cast

from bioetl.domain.normalization.profiles._standard_profile_rule_components import (
    RuleComponentSpec,
)

__all__ = ["StandardProfileSpec", "coerce_standard_profile_spec"]


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
_STANDARD_PROFILE_FIELD_NAMES = tuple(
    field.name for field in fields(StandardProfileSpec)
)


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


def _require_standard_profile_fields(
    spec: StandardProfileSpec | None,
    overrides: dict[str, object],
) -> None:
    for field_name in _STANDARD_PROFILE_REQUIRED_FIELDS:
        _resolve_standard_profile_value(
            field_name=field_name,
            spec=spec,
            overrides=overrides,
        )


def coerce_standard_profile_spec(
    spec: StandardProfileSpec | None,
    overrides: dict[str, object],
) -> StandardProfileSpec:
    """Build a fully-populated standard profile spec from explicit args/overrides."""
    _require_standard_profile_fields(spec, overrides)
    resolved_values = {
        field_name: _resolve_standard_profile_value(
            field_name=field_name,
            spec=spec,
            overrides=overrides,
        )
        for field_name in _STANDARD_PROFILE_FIELD_NAMES
    }
    return cast(StandardProfileSpec, StandardProfileSpec(**resolved_values))
