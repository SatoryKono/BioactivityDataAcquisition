"""Shared types for preflight governance services."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from bioetl.domain.types.validation_severity import ValidationSeverity


class GovernancePolicy(Enum):
    """Execution governance policies."""

    BLOCK_ON_ANY_ISSUE = "block_on_any_issue"
    BLOCK_ON_BLOCKERS_ONLY = "block_on_blockers_only"
    WARNING_ONLY = "warning_only"
    CI_STRICT = "ci_strict"
    CI_RELAXED = "ci_relaxed"


@dataclass(frozen=True)
class PreflightGovernanceConfig:
    """Configuration for preflight governance."""

    policy: GovernancePolicy
    ci_integration: bool = False
    fail_fast: bool = True
    issue_code_overrides: Mapping[str, ValidationSeverity] | None = None

    def __post_init__(self) -> None:
        """Snapshot overrides as an immutable mapping proxy."""
        if self.issue_code_overrides is None:
            return
        object.__setattr__(
            self,
            "issue_code_overrides",
            MappingProxyType(dict(self.issue_code_overrides)),
        )

    def __hash__(self) -> int:
        overrides = self.issue_code_overrides
        override_key = (
            None
            if overrides is None
            else frozenset((key, value) for key, value in overrides.items())
        )
        return hash(
            (
                self.policy,
                self.ci_integration,
                self.fail_fast,
                override_key,
            )
        )
