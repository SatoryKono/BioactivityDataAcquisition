"""Config-surface derived optionality for structural Silver policy.

This module implements the pragmatic v1 resolver where field optionality is
derived from the current config surface instead of an explicit field-level
policy overlay.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

OptionalitySource = Literal[
    "field_policy_optional_false",
    "field_policy_optional_true",
    "silver_required_fields",
    "dq_required_validation",
    "dq_not_null_validation",
    "dq_key_nullability",
    "default_optional",
]

FRAMEWORK_MANAGED_FIELDS = frozenset(
    {
        "entity_id",
        "content_hash",
        "_run_id",
        "_run_type",
        "_source_batch_id",
        "_ingestion_ts",
        "_index",
        "_dq_warn",
        "_dq_error",
        "_state",
    }
)


@dataclass(frozen=True, slots=True)
class ResolvedOptionalityResult:
    """Resolved optionality and its source tags for one field."""

    optional: bool
    sources: tuple[OptionalitySource, ...]


@dataclass(frozen=True, slots=True)
class ConfigSurfaceOptionalityResolver:
    """Resolve field optionality from current config and DQ semantics."""

    explicit_optional_overrides: dict[str, bool]
    silver_required_fields: frozenset[str]
    dq_required_fields: frozenset[str]
    dq_not_null_fields: frozenset[str]
    dq_key_nonnullable_fields: frozenset[str]

    @classmethod
    def from_domain_config(
        cls, domain_config: object
    ) -> ConfigSurfaceOptionalityResolver:
        """Build resolver from current pipeline domain config."""
        return cls(
            explicit_optional_overrides=_collect_explicit_optional_overrides(
                domain_config
            ),
            silver_required_fields=_collect_silver_required_fields(domain_config),
            dq_required_fields=_collect_dq_fields(
                domain_config,
                validation_type="required",
            ),
            dq_not_null_fields=_collect_dq_fields(
                domain_config,
                validation_type="not_null",
            ),
            dq_key_nonnullable_fields=_collect_nonnullable_key_fields(domain_config),
        )

    def resolve(self, field_name: str) -> ResolvedOptionalityResult:
        """Resolve effective optionality for one business field."""
        explicit_override = self.explicit_optional_overrides.get(field_name)
        if explicit_override is not None:
            source: OptionalitySource = (
                "field_policy_optional_true"
                if explicit_override
                else "field_policy_optional_false"
            )
            return ResolvedOptionalityResult(
                optional=explicit_override,
                sources=(source,),
            )

        sources: list[OptionalitySource] = []
        if field_name in self.silver_required_fields:
            sources.append("silver_required_fields")
        if field_name in self.dq_required_fields:
            sources.append("dq_required_validation")
        if field_name in self.dq_not_null_fields:
            sources.append("dq_not_null_validation")
        if field_name in self.dq_key_nonnullable_fields:
            sources.append("dq_key_nullability")

        if sources:
            return ResolvedOptionalityResult(optional=False, sources=tuple(sources))
        return ResolvedOptionalityResult(optional=True, sources=("default_optional",))


# Backward-compatible alias retained for existing imports/tests.
ResolvedOptionality = ResolvedOptionalityResult


def _collect_explicit_optional_overrides(domain_config: object) -> dict[str, bool]:
    """Collect field-level optionality overrides from domain config."""
    overrides: dict[str, bool] = {}
    for policy in getattr(domain_config, "field_policy", ()):
        field_name = getattr(policy, "field", None)
        optional = getattr(policy, "optional", None)
        if (
            isinstance(field_name, str)
            and not is_framework_managed_field(field_name)
            and isinstance(optional, bool)
        ):
            overrides[field_name] = optional
    return overrides


def _collect_silver_required_fields(domain_config: object) -> frozenset[str]:
    """Collect required fields explicitly declared in silver filters."""
    silver_filters = getattr(domain_config, "silver_filters", None)
    if silver_filters is None:
        return frozenset()
    return frozenset(getattr(silver_filters, "required_fields", ()))


def _iter_dq_field_validations(domain_config: object) -> tuple[object, ...]:
    """Return DQ field validations as a stable iterable."""
    dq_config = getattr(domain_config, "dq", None)
    if dq_config is None:
        return ()
    return tuple(getattr(dq_config, "field_validations", ()))


def _collect_dq_fields(
    domain_config: object,
    *,
    validation_type: str,
) -> frozenset[str]:
    """Collect DQ fields for one validation type."""
    fields: set[str] = set()
    for validation in _iter_dq_field_validations(domain_config):
        field_name = getattr(validation, "field", None)
        if not field_name:
            continue
        if getattr(validation, "validation_type", None) == validation_type:
            fields.add(field_name)
    return frozenset(fields)


def _collect_nonnullable_key_fields(domain_config: object) -> frozenset[str]:
    """Collect DQ key fields explicitly marked as non-nullable."""
    dq_config = getattr(domain_config, "dq", None)
    if dq_config is None:
        return frozenset()

    fields: set[str] = set()
    for key_rule in getattr(dq_config, "key_nullability_rules", ()):
        if getattr(key_rule, "nullable", True):
            continue
        field_name = getattr(key_rule, "field", None)
        if field_name:
            fields.add(field_name)
    return frozenset(fields)


def is_framework_managed_field(field_name: str) -> bool:
    """Return True for framework/system-managed Silver columns."""
    return field_name in FRAMEWORK_MANAGED_FIELDS


__all__ = [
    "FRAMEWORK_MANAGED_FIELDS",
    "ConfigSurfaceOptionalityResolver",
    "OptionalitySource",
    "ResolvedOptionalityResult",
    "is_framework_managed_field",
]
