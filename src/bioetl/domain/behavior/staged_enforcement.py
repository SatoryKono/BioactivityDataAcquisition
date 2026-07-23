"""Enhanced staged enforcement framework for CI checks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TypedDict

from bioetl.domain.types import JsonDict


class EnforcementStage(Enum):
    """Enforcement stages for CI checks."""

    OBSERVE = "observe"  # Log only, no impact
    SOFT_FAIL = "soft_fail"  # Warning, non-blocking
    HARD_FAIL = "hard_fail"  # Blocking failure


class CheckResult:
    """Result of a staged CI check."""

    def __init__(
        self,
        check_name: str,
        passed: bool,
        message: str,
        details: JsonDict | None = None,
        diagnostics: JsonDict | None = None,
    ):
        self.check_name = check_name
        self.passed = passed
        self.message = message
        self.details = details or {}
        self.diagnostics = diagnostics or {}

    def to_dict(self) -> JsonDict:
        """Convert to dictionary for reporting."""
        return {
            "check_name": self.check_name,
            "passed": self.passed,
            "message": self.message,
            "details": self.details,
            "diagnostics": self.diagnostics,
        }


@dataclass(frozen=True)
class EnforcementPolicy:
    """Policy for staged enforcement."""

    check_name: str
    current_stage: EnforcementStage
    failure_threshold: float = 0.0
    warning_threshold: float = 0.5
    observe_until: str | None = None  # "YYYY-MM-DD"
    soft_fail_until: str | None = None  # "YYYY-MM-DD"

    def get_effective_stage(self, failure_rate: float) -> EnforcementStage:
        """Resolve the effective enforcement stage for the observed failure rate."""
        if failure_rate >= self.failure_threshold:
            return EnforcementStage.HARD_FAIL
        if failure_rate >= self.warning_threshold:
            return EnforcementStage.SOFT_FAIL
        return EnforcementStage.OBSERVE


class StagedEnforcementEngine:
    """Engine for managing staged CI enforcement."""

    def __init__(self, policies: dict[str, EnforcementPolicy] | None = None) -> None:
        # Defaults only when policies is None; explicit {} disables all policies.
        self.policies = (
            _build_default_policies() if policies is None else dict(policies)
        )
        self.results: list[CheckResult] = []
        self._contract_policies = {
            name: self.policies[name]
            for name in _CONTRACT_POLICY_NAMES
            if name in self.policies
        }

    def register_result(self, result: CheckResult) -> None:
        """Register a check result."""
        self.results.append(result)

    def get_enforcement_verdict(
        self, check_name: str, failure_count: int, total_count: int
    ) -> tuple[EnforcementStage, str]:
        """Determine enforcement verdict for a check."""
        if total_count == 0:
            return EnforcementStage.OBSERVE, "No items to check"

        failure_rate = failure_count / total_count
        policy = self.policies.get(check_name)

        if not policy:
            return EnforcementStage.OBSERVE, "No policy defined"

        threshold_stage = policy.get_effective_stage(failure_rate)
        effective_stage = _stage_allowed_by_current_policy(
            threshold_stage, policy.current_stage
        )
        rollout_capped = threshold_stage != effective_stage

        if effective_stage == EnforcementStage.HARD_FAIL:
            message = (
                f"Hard fail threshold exceeded "
                f"({failure_rate:.1%} >= {policy.failure_threshold:.1%})"
            )
        elif effective_stage == EnforcementStage.SOFT_FAIL:
            message = (
                f"Soft fail threshold exceeded "
                f"({failure_rate:.1%} >= {policy.warning_threshold:.1%})"
            )
        elif rollout_capped:
            message = (
                f"Observation mode due to rollout cap "
                f"(threshold_stage={threshold_stage.value}, "
                f"current_stage={policy.current_stage.value}, "
                f"failure_rate={failure_rate:.1%})"
            )
        else:
            message = (
                f"Observation mode "
                f"({failure_rate:.1%} < {policy.warning_threshold:.1%})"
            )

        return effective_stage, message

    def generate_diagnostics_report(self) -> JsonDict:
        """Generate comprehensive diagnostics report."""
        grouped_results = _group_results_by_check(self.results)
        return _build_diagnostics_report(
            results=self.results,
            grouped_results=grouped_results,
            policies=self.policies,
        )

    def should_block_ci(self) -> bool:
        """Determine if CI should be blocked based on results."""
        for result in self.results:
            policy = self.policies.get(result.check_name)
            if not policy:
                continue

            # For now, only hard fails block CI
            # This can be made configurable later
            if not result.passed:
                failure_rate = 1.0  # Single failure
                if (
                    _stage_allowed_by_current_policy(
                        policy.get_effective_stage(failure_rate), policy.current_stage
                    )
                    == EnforcementStage.HARD_FAIL
                ):
                    return True
        return False


def _stage_allowed_by_current_policy(
    threshold_stage: EnforcementStage, configured_stage: EnforcementStage
) -> EnforcementStage:
    """Cap threshold-derived enforcement by the configured rollout stage."""
    order = {
        EnforcementStage.OBSERVE: 0,
        EnforcementStage.SOFT_FAIL: 1,
        EnforcementStage.HARD_FAIL: 2,
    }
    return (
        threshold_stage
        if order[threshold_stage] <= order[configured_stage]
        else configured_stage
    )


def create_enforcement_engine() -> StagedEnforcementEngine:
    """Factory function for enforcement engine."""
    return StagedEnforcementEngine()


class _DefaultPolicySpec(TypedDict):
    check_name: str
    current_stage: EnforcementStage
    failure_threshold: float
    warning_threshold: float


_DEFAULT_POLICY_SPECS: tuple[_DefaultPolicySpec, ...] = (
    {
        "check_name": "fixture_governance",
        "current_stage": EnforcementStage.SOFT_FAIL,
        "failure_threshold": 0.8,
        "warning_threshold": 0.3,
    },
    {
        "check_name": "checkpoint_compatibility",
        "current_stage": EnforcementStage.OBSERVE,
        "failure_threshold": 0.9,
        "warning_threshold": 0.4,
    },
    {
        "check_name": "effective_config_stability",
        "current_stage": EnforcementStage.OBSERVE,
        "failure_threshold": 0.7,
        "warning_threshold": 0.2,
    },
    {
        "check_name": "contract_identity",
        "current_stage": EnforcementStage.SOFT_FAIL,
        "failure_threshold": 0.7,
        "warning_threshold": 0.2,
    },
    {
        "check_name": "registry_consistency",
        "current_stage": EnforcementStage.OBSERVE,
        "failure_threshold": 0.8,
        "warning_threshold": 0.3,
    },
    {
        "check_name": "schema_compatibility",
        "current_stage": EnforcementStage.OBSERVE,
        "failure_threshold": 0.9,
        "warning_threshold": 0.4,
    },
)

_CONTRACT_POLICY_NAMES = frozenset(
    {"contract_identity", "registry_consistency", "schema_compatibility"}
)


def _build_default_policies() -> dict[str, EnforcementPolicy]:
    return {
        spec["check_name"]: EnforcementPolicy(
            check_name=spec["check_name"],
            current_stage=spec["current_stage"],
            failure_threshold=spec["failure_threshold"],
            warning_threshold=spec["warning_threshold"],
        )
        for spec in _DEFAULT_POLICY_SPECS
    }


def _serialize_policies(policies: dict[str, EnforcementPolicy]) -> JsonDict:
    """Serialize enforcement policies for diagnostics output."""
    return {
        name: {
            "current_stage": policy.current_stage.value,
            "failure_threshold": policy.failure_threshold,
            "warning_threshold": policy.warning_threshold,
            "observe_until": policy.observe_until,
            "soft_fail_until": policy.soft_fail_until,
        }
        for name, policy in policies.items()
    }


def _passed_checks(results: list[CheckResult]) -> int:
    """Count passed checks."""
    return sum(1 for result in results if result.passed)


def _failed_checks(results: list[CheckResult]) -> int:
    """Count failed checks."""
    return sum(1 for result in results if not result.passed)


def _check_details(results: list[CheckResult]) -> JsonDict:
    """Serialize all check results keyed by check name."""
    return {result.check_name: result.to_dict() for result in results}


def _pass_rates(grouped_results: dict[str, list[CheckResult]]) -> JsonDict:
    """Calculate pass rates by check name."""
    return {
        check_name: _calculate_pass_rate(results)
        for check_name, results in grouped_results.items()
    }


def _build_diagnostics_report(
    results: list[CheckResult],
    grouped_results: dict[str, list[CheckResult]],
    policies: dict[str, EnforcementPolicy],
) -> JsonDict:
    """Build diagnostics report payload from engine state."""
    return {
        "total_checks": len(results),
        "passed_checks": _passed_checks(results),
        "failed_checks": _failed_checks(results),
        "check_details": _check_details(results),
        "enforcement_policies": _serialize_policies(policies),
        "pass_rates": _pass_rates(grouped_results),
    }


def _group_results_by_check(results: list[CheckResult]) -> dict[str, list[CheckResult]]:
    """Group check results by check name."""
    grouped: dict[str, list[CheckResult]] = {}
    for result in results:
        grouped.setdefault(result.check_name, []).append(result)
    return grouped


def _calculate_pass_rate(results: list[CheckResult]) -> float:
    """Calculate pass rate for a single check group."""
    if not results:
        return 0.0
    return sum(1 for result in results if result.passed) / len(results)
