"""Typed spec and coercion helpers for standard normalization profiles."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
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
    return StandardProfileSpec(
        profile_name=cast(
            str,
            _resolve_standard_profile_value(
                field_name="profile_name",
                spec=spec,
                overrides=overrides,
            ),
        ),
        description=cast(
            str,
            _resolve_standard_profile_value(
                field_name="description",
                spec=spec,
                overrides=overrides,
            ),
        ),
        schema_fields=cast(
            Collection[str],
            _resolve_standard_profile_value(
                field_name="schema_fields",
                spec=spec,
                overrides=overrides,
            ),
        ),
        meta_fields=cast(
            Collection[str],
            _resolve_standard_profile_value(
                field_name="meta_fields",
                spec=spec,
                overrides=overrides,
            ),
        ),
        title_fields=cast(
            Collection[str],
            _resolve_standard_profile_value(
                field_name="title_fields",
                spec=spec,
                overrides=overrides,
            ),
        ),
        abstract_fields=cast(
            Collection[str],
            _resolve_standard_profile_value(
                field_name="abstract_fields",
                spec=spec,
                overrides=overrides,
            ),
        ),
        doi_fields=cast(
            Collection[str],
            _resolve_standard_profile_value(
                field_name="doi_fields",
                spec=spec,
                overrides=overrides,
            ),
        ),
        pmid_fields=cast(
            Collection[str],
            _resolve_standard_profile_value(
                field_name="pmid_fields",
                spec=spec,
                overrides=overrides,
            ),
        ),
        pmc_id_fields=cast(
            Collection[str],
            _resolve_standard_profile_value(
                field_name="pmc_id_fields",
                spec=spec,
                overrides=overrides,
            ),
        ),
        date_fields=cast(
            Collection[str],
            _resolve_standard_profile_value(
                field_name="date_fields",
                spec=spec,
                overrides=overrides,
            ),
        ),
        int_fields=cast(
            Collection[str],
            _resolve_standard_profile_value(
                field_name="int_fields",
                spec=spec,
                overrides=overrides,
            ),
        ),
        float_fields=cast(
            Collection[str],
            _resolve_standard_profile_value(
                field_name="float_fields",
                spec=spec,
                overrides=overrides,
            ),
        ),
        set_like_fields=cast(
            Collection[str],
            _resolve_standard_profile_value(
                field_name="set_like_fields",
                spec=spec,
                overrides=overrides,
            ),
        ),
        json_string_fields=cast(
            Collection[str],
            _resolve_standard_profile_value(
                field_name="json_string_fields",
                spec=spec,
                overrides=overrides,
            ),
        ),
        strict_json_fields=cast(
            Collection[str],
            _resolve_standard_profile_value(
                field_name="strict_json_fields",
                spec=spec,
                overrides=overrides,
            ),
        ),
        boolean_fields=cast(
            Collection[str],
            _resolve_standard_profile_value(
                field_name="boolean_fields",
                spec=spec,
                overrides=overrides,
            ),
        ),
        flag_fields=cast(
            Collection[str],
            _resolve_standard_profile_value(
                field_name="flag_fields",
                spec=spec,
                overrides=overrides,
            ),
        ),
        operator_fields=cast(
            Collection[str],
            _resolve_standard_profile_value(
                field_name="operator_fields",
                spec=spec,
                overrides=overrides,
            ),
        ),
        ontology_id_fields=cast(
            Collection[str],
            _resolve_standard_profile_value(
                field_name="ontology_id_fields",
                spec=spec,
                overrides=overrides,
            ),
        ),
        enum_fields=cast(
            Mapping[str, frozenset[str]] | None,
            _resolve_standard_profile_value(
                field_name="enum_fields",
                spec=spec,
                overrides=overrides,
            ),
        ),
        case_fields=cast(
            Mapping[str, frozenset[str] | None] | None,
            _resolve_standard_profile_value(
                field_name="case_fields",
                spec=spec,
                overrides=overrides,
            ),
        ),
        unit_fields=cast(
            Collection[str] | None,
            _resolve_standard_profile_value(
                field_name="unit_fields",
                spec=spec,
                overrides=overrides,
            ),
        ),
        null_fields=cast(
            Collection[str] | None,
            _resolve_standard_profile_value(
                field_name="null_fields",
                spec=spec,
                overrides=overrides,
            ),
        ),
        special_rules=cast(
            Mapping[str, RuleComponentSpec] | None,
            _resolve_standard_profile_value(
                field_name="special_rules",
                spec=spec,
                overrides=overrides,
            ),
        ),
    )
