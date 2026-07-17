"""Validation functions for normalization profile contracts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.normalization.profiles.base import FieldRule


def _normalize_field_rules(
    field_rules: Mapping[str, FieldRule],
) -> dict[str, FieldRule]:
    """Normalize field rules to sorted dict."""
    return dict(sorted(field_rules.items(), key=lambda item: item[0]))


def _normalize_field_aliases(field_aliases: Mapping[str, str]) -> dict[str, str]:
    """Normalize field aliases to sorted dict."""
    return dict(
        sorted(
            ((str(alias), str(target)) for alias, target in field_aliases.items()),
            key=lambda item: item[0],
        )
    )


def _validate_field_rule_keys(field_rules: Mapping[str, FieldRule]) -> None:
    """Validate that field rule keys match field names."""
    for field_name, rule in field_rules.items():
        if field_name != rule.field_name:
            raise ValueError(
                f"FieldRule key {field_name!r} does not match field_name {rule.field_name!r}"
            )


def _validate_field_aliases(
    *,
    field_rules: Mapping[str, FieldRule],
    field_aliases: Mapping[str, str],
) -> None:
    """Validate field aliases don't shadow canonical fields."""
    for alias, target in field_aliases.items():
        if alias in field_rules:
            raise ValueError(f"field_aliases cannot shadow canonical field {alias!r}")
        if target not in field_rules:
            raise ValueError(
                f"field_alias target {target!r} is missing from field_rules"
            )


def _validate_meta_fields(
    *,
    meta_fields: frozenset[str],
    field_rules: Mapping[str, FieldRule],
) -> None:
    """Validate that meta fields are present in field rules."""
    if meta_fields.issubset(field_rules.keys()):
        return
    missing = sorted(meta_fields.difference(field_rules.keys()))
    raise ValueError(
        f"meta_fields must be present in field_rules: {', '.join(missing)}"
    )


def _normalize_profile_contract(
    *,
    field_rules: Mapping[str, FieldRule],
    field_aliases: Mapping[str, str],
    meta_fields: frozenset[str],
) -> tuple[dict[str, FieldRule], dict[str, str]]:
    """Normalize and validate profile contract."""
    normalized_rules = _normalize_field_rules(field_rules)
    normalized_aliases = _normalize_field_aliases(field_aliases)
    if not normalized_rules:
        raise ValueError("field_rules cannot be empty")
    _validate_field_rule_keys(normalized_rules)
    _validate_field_aliases(
        field_rules=normalized_rules,
        field_aliases=normalized_aliases,
    )
    _validate_meta_fields(
        meta_fields=meta_fields,
        field_rules=normalized_rules,
    )
    return normalized_rules, normalized_aliases
