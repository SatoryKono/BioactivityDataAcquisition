"""Config-surface derived optionality for structural Silver policy.

This module implements the pragmatic v1 resolver where field optionality is
derived from the current config surface instead of an explicit field-level
policy overlay.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

OptionalitySource = Literal[
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
class ResolvedOptionality:
    """Resolved optionality and its source tags for one field."""

    optional: bool
    sources: tuple[OptionalitySource, ...]


@dataclass(frozen=True, slots=True)
class ConfigSurfaceOptionalityResolver:
    """Resolve field optionality from current config and DQ semantics."""

    silver_required_fields: frozenset[str]
    dq_required_fields: frozenset[str]
    dq_not_null_fields: frozenset[str]
    dq_key_nonnullable_fields: frozenset[str]

    @classmethod
    def from_domain_config(
        cls, domain_config: object
    ) -> ConfigSurfaceOptionalityResolver:
        """Build resolver from current pipeline domain config."""
        silver_required_fields: set[str] = set()
        dq_required_fields: set[str] = set()
        dq_not_null_fields: set[str] = set()
        dq_key_nonnullable_fields: set[str] = set()

        silver_filters = getattr(domain_config, "silver_filters", None)
        if silver_filters is not None:
            silver_required_fields.update(
                getattr(silver_filters, "required_fields", ())
            )

        dq_config = getattr(domain_config, "dq", None)
        if dq_config is not None:
            for validation in getattr(dq_config, "field_validations", ()):
                field_name = getattr(validation, "field", None)
                if not field_name:
                    continue
                validation_type = getattr(validation, "validation_type", None)
                if validation_type == "required":
                    dq_required_fields.add(field_name)
                elif validation_type == "not_null":
                    dq_not_null_fields.add(field_name)

            for key_rule in getattr(dq_config, "key_nullability_rules", ()):
                if getattr(key_rule, "nullable", True):
                    continue
                field_name = getattr(key_rule, "field", None)
                if field_name:
                    dq_key_nonnullable_fields.add(field_name)

        return cls(
            silver_required_fields=frozenset(silver_required_fields),
            dq_required_fields=frozenset(dq_required_fields),
            dq_not_null_fields=frozenset(dq_not_null_fields),
            dq_key_nonnullable_fields=frozenset(dq_key_nonnullable_fields),
        )

    def resolve(self, field_name: str) -> ResolvedOptionality:
        """Resolve effective optionality for one business field."""
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
            return ResolvedOptionality(optional=False, sources=tuple(sources))
        return ResolvedOptionality(optional=True, sources=("default_optional",))


def is_framework_managed_field(field_name: str) -> bool:
    """Return True for framework/system-managed Silver columns."""
    return field_name in FRAMEWORK_MANAGED_FIELDS


__all__ = [
    "ConfigSurfaceOptionalityResolver",
    "FRAMEWORK_MANAGED_FIELDS",
    "OptionalitySource",
    "ResolvedOptionality",
    "is_framework_managed_field",
]
