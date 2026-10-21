"""Owning source of executable DQ contract rules.

``DQPolicyResolver`` resolves dispositions for a rule id. It does not load a
rule bundle from ``DQPolicyRef.contract_ref``. Executable rules are the
field, cross-field, and conditional validations already materialized on the
bound ``DQConfig`` by the config loaders. Loading them is a separate step
from disposition resolution.
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.config.dq import DQConfig
from bioetl.domain.types.dq_contracts import DQDisposition

__all__ = [
    "ExecutableContractRules",
    "has_explicit_outcome_policy",
    "load_executable_contract_rules",
    "override_disposition",
]

_RULE_SOURCE = (
    "dq_config.field_validations,"
    "dq_config.cross_field_validations,"
    "dq_config.conditional_validations"
)


@dataclass(frozen=True, slots=True)
class ExecutableContractRules:
    """Contract rules loaded from the bound DQ configuration."""

    field_validations: tuple[object, ...]
    cross_field_validations: tuple[object, ...]
    conditional_validations: tuple[object, ...]
    source: str = _RULE_SOURCE

    @property
    def is_empty(self) -> bool:
        """Whether the loaded bundle has no executable rules."""
        return not (
            self.field_validations
            or self.cross_field_validations
            or self.conditional_validations
        )


def load_executable_contract_rules(
    config: DQConfig | None,
) -> ExecutableContractRules:
    """Load executable rules from ``config`` without consulting ``contract_ref``."""
    if config is None:
        return ExecutableContractRules((), (), ())
    return ExecutableContractRules(
        field_validations=tuple(config.field_validations),
        cross_field_validations=tuple(config.cross_field_validations),
        conditional_validations=tuple(config.conditional_validations),
    )


def has_explicit_outcome_policy(config: DQConfig | None) -> bool:
    """Whether outcome routing may replace the default fail-closed validate path.

    A default ``DQConfig`` with no rules and no disposition overrides keeps
    batch-level ``.validate()``. Rules or overrides are the explicit policy.
    """
    if config is None:
        return False
    if not load_executable_contract_rules(config).is_empty:
        return True
    return bool(config.disposition_overrides)


def override_disposition(
    config: DQConfig | None,
    rule_id: str,
) -> DQDisposition | None:
    """Return an explicit per-rule disposition override, when configured."""
    if config is None:
        return None
    found = _lookup_override(config.disposition_overrides, rule_id)
    if isinstance(found, DQDisposition):
        return found
    return None


def _lookup_override(overrides: object, rule_id: str) -> object:
    if isinstance(overrides, dict):
        return overrides.get(rule_id)
    if isinstance(overrides, (tuple, list)):
        return dict(overrides).get(rule_id)
    return None
