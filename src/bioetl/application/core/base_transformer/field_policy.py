"""Resolved field-level structural policy for transformed Silver records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from bioetl.application.core.base_transformer.optionality import (
    ConfigSurfaceOptionalityResolver,
    OptionalitySource,
    is_framework_managed_field,
)

FieldCoercionPolicy = Literal["default", "no_string_coercion"]

@dataclass(frozen=True, slots=True, kw_only=True)
class FieldPolicySpec:
    """Shared resolved field-policy contract surface."""

    optional: bool
    optional_sources: tuple[OptionalitySource, ...]
    empty_as_missing: bool | None = None
    coercion_policy: FieldCoercionPolicy = "default"
    boolean_true_values: tuple[str, ...] = ()
    boolean_false_values: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class ResolvedFieldPolicy(FieldPolicySpec):
    """Resolved structural policy contract for one field."""

@dataclass(frozen=True, slots=True)
class FieldPolicyResolver:
    """Resolve explicit field-level structural policy with config fallback."""

    optionality_resolver: ConfigSurfaceOptionalityResolver
    explicit_field_policy: dict[str, object]

    @classmethod
    def from_domain_config(cls, domain_config: object) -> FieldPolicyResolver:
        """Build resolver from the pipeline domain config."""
        return cls(
            optionality_resolver=ConfigSurfaceOptionalityResolver.from_domain_config(
                domain_config
            ),
            explicit_field_policy=_collect_explicit_field_policy(domain_config),
        )

    def resolve(self, field_name: str) -> ResolvedFieldPolicy:
        """Resolve the effective structural policy for one business field."""
        explicit_policy = self.explicit_field_policy.get(field_name)
        resolved_optionality = self.optionality_resolver.resolve(field_name)
        if explicit_policy is None:
            return ResolvedFieldPolicy(
                optional=resolved_optionality.optional,
                optional_sources=resolved_optionality.sources,
            )

        return ResolvedFieldPolicy(
            optional=resolved_optionality.optional,
            optional_sources=resolved_optionality.sources,
            empty_as_missing=getattr(explicit_policy, "empty_as_missing", None),
            coercion_policy=_resolve_field_coercion_policy(explicit_policy),
            boolean_true_values=tuple(
                getattr(explicit_policy, "boolean_true_values", ())
            ),
            boolean_false_values=tuple(
                getattr(explicit_policy, "boolean_false_values", ())
            ),
        )

def _collect_explicit_field_policy(domain_config: object) -> dict[str, object]:
    """Collect explicit field-level structural policy overrides from config."""
    explicit_policy: dict[str, object] = {}
    for policy in getattr(domain_config, "field_policy", ()):
        field_name = getattr(policy, "field", None)
        if not isinstance(field_name, str) or is_framework_managed_field(field_name):
            continue
        explicit_policy[field_name] = policy
    return explicit_policy

__all__ = [
    "FieldCoercionPolicy",
    "FieldPolicyResolver",
    "FieldPolicySpec",
    "ResolvedFieldPolicy",
]

def _resolve_field_coercion_policy(explicit_policy: object) -> FieldCoercionPolicy:
    """Return one validated coercion policy with a conservative default."""
    coercion_policy = getattr(explicit_policy, "coercion_policy", None)
    if coercion_policy == "no_string_coercion":
        return "no_string_coercion"
    return "default"
