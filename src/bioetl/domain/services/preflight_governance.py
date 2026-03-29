"""Preflight governance service for composite execution."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum

from bioetl.domain.services.preflight_governance_reporting import (
    build_validation_summary,
)
from bioetl.domain.types import JsonDict
from bioetl.domain.types.validation_result import (
    CompositeValidationReport,
    ValidationIssue,
    ValidationResult,
)
from bioetl.domain.types.validation_severity import (
    ValidationLayer,
    ValidationSeverity,
)


class GovernancePolicy(Enum):
    """Execution governance policies."""

    BLOCK_ON_ANY_ISSUE = "block_on_any_issue"
    BLOCK_ON_BLOCKERS_ONLY = "block_on_blockers_only"
    WARNING_ONLY = "warning_only"
    CI_STRICT = "ci_strict"
    CI_RELAXED = "ci_relaxed"


_BLOCKING_POLICIES: frozenset[GovernancePolicy] = frozenset(
    {
        GovernancePolicy.BLOCK_ON_ANY_ISSUE,
        GovernancePolicy.BLOCK_ON_BLOCKERS_ONLY,
        GovernancePolicy.CI_STRICT,
        GovernancePolicy.CI_RELAXED,
    }
)


@dataclass(frozen=True)
class PreflightGovernanceConfig:
    """Configuration for preflight governance."""

    policy: GovernancePolicy
    ci_integration: bool = False
    fail_fast: bool = True
    issue_code_overrides: dict[str, ValidationSeverity] | None = None


class PreflightGovernanceService:
    """Service for preflight execution governance."""

    def __init__(self, config: PreflightGovernanceConfig | None = None):
        self.config = config or PreflightGovernanceConfig(
            policy=GovernancePolicy.BLOCK_ON_BLOCKERS_ONLY
        )

    def apply_governance(
        self,
        validation_report: CompositeValidationReport,
        execution_context: JsonDict | None = None,
        config: PreflightGovernanceConfig | None = None,
    ) -> JsonDict:
        """Apply governance policy to validation report."""
        execution_context = execution_context or {}
        active_config = config or self.config
        report_with_overrides = self._apply_issue_overrides(
            validation_report,
            active_config,
        )
        execution_decision = self._determine_execution_decision(
            report_with_overrides,
            active_config,
        )
        return self._generate_governance_report(
            report_with_overrides,
            execution_decision,
            execution_context,
            active_config,
        )

    def _apply_issue_overrides(
        self,
        report: CompositeValidationReport,
        config: PreflightGovernanceConfig,
    ) -> CompositeValidationReport:
        """Apply severity overrides from configuration."""
        if not config.issue_code_overrides:
            return report
        return CompositeValidationReport(
            structural_result=self._rebuild_validation_result(
                report.structural_result,
                ValidationLayer.STRUCTURAL,
                config,
            ),
            deep_preflight_result=self._rebuild_validation_result(
                report.deep_preflight_result,
                ValidationLayer.DEEP_PREFLIGHT,
                config,
            ),
            runtime_guard_result=self._runtime_result_with_overrides(
                report.runtime_guard_result,
                config,
            ),
        )

    def _runtime_result_with_overrides(
        self,
        runtime_result: ValidationResult | None,
        config: PreflightGovernanceConfig,
    ) -> ValidationResult | None:
        """Apply overrides to runtime-guard result when present."""
        if runtime_result is None:
            return None
        return self._rebuild_validation_result(
            runtime_result,
            ValidationLayer.RUNTIME_GUARD,
            config,
        )

    def _rebuild_validation_result(
        self,
        result: ValidationResult,
        layer: ValidationLayer,
        config: PreflightGovernanceConfig,
    ) -> ValidationResult:
        """Rebuild one validation result after applying issue overrides."""
        return ValidationResult(
            issues=self._apply_overrides_to_issues(result.issues, config),
            validation_layer=layer,
            execution_context=result.execution_context,
            timestamp=result.timestamp,
        )

    def _apply_overrides_to_issues(
        self,
        issues: list[ValidationIssue],
        config: PreflightGovernanceConfig,
    ) -> list[ValidationIssue]:
        """Apply severity overrides to individual issues."""
        if not config.issue_code_overrides:
            return issues

        overridden_issues: list[ValidationIssue] = []
        for issue in issues:
            override = config.issue_code_overrides.get(issue.code.value)
            overridden_issues.append(self._apply_issue_override(issue, override))

        return overridden_issues

    def _apply_issue_override(
        self,
        issue: ValidationIssue,
        override: ValidationSeverity | None,
    ) -> ValidationIssue:
        """Return issue with overridden severity when configuration requires it."""
        if override is None:
            return issue
        return replace(issue, severity=override)

    def _determine_execution_decision(
        self,
        report: CompositeValidationReport,
        config: PreflightGovernanceConfig,
    ) -> JsonDict:
        """Determine execution decision based on governance policy."""
        policy = config.policy
        if policy is GovernancePolicy.WARNING_ONLY:
            return {
                "execution_allowed": True,
                "reason": "warning_only_mode",
                "policy_applied": policy.value,
            }

        blocked, reason = self._resolve_policy_block_state(report, policy)
        if blocked:
            return {
                "execution_allowed": False,
                "reason": reason,
                "policy_applied": policy.value,
            }
        return {
            "execution_allowed": True,
            "reason": "no_blocking_issues",
            "policy_applied": policy.value,
        }

    def _has_effective_blockers(self, report: CompositeValidationReport) -> bool:
        """Check if report has any effective blockers after considering overrides."""
        all_issues = report.get_all_issues()
        return any(self._is_effective_blocker(issue) for issue in all_issues)

    def _resolve_policy_block_state(
        self,
        report: CompositeValidationReport,
        policy: GovernancePolicy,
    ) -> tuple[bool, str]:
        """Resolve whether a policy blocks execution and why."""
        checks: dict[GovernancePolicy, tuple[bool, str]] = {
            GovernancePolicy.BLOCK_ON_ANY_ISSUE: (
                report.has_any_issues(),
                "any_issue_found",
            ),
            GovernancePolicy.BLOCK_ON_BLOCKERS_ONLY: (
                self._has_effective_blockers(report),
                "blocker_issues_found",
            ),
            GovernancePolicy.CI_STRICT: (
                report.has_any_issues(),
                "ci_strict_mode_violation",
            ),
            GovernancePolicy.CI_RELAXED: (
                self._has_effective_blockers(report),
                "ci_relaxed_blockers_found",
            ),
        }
        return checks.get(policy, (False, "no_blocking_issues"))

    def _generate_governance_report(
        self,
        report: CompositeValidationReport,
        execution_decision: JsonDict,
        execution_context: JsonDict,
        config: PreflightGovernanceConfig,
    ) -> JsonDict:
        """Generate comprehensive governance report."""
        return {
            "governance_metadata": self._build_governance_metadata(config),
            "execution_decision": execution_decision,
            "validation_summary": build_validation_summary(report),
            "execution_context": execution_context,
            "detailed_issues": self._format_detailed_issues(report, config),
        }

    @staticmethod
    def _build_governance_metadata(config: PreflightGovernanceConfig) -> JsonDict:
        """Build governance metadata for reporting."""
        return {
            "policy": config.policy.value,
            "ci_integration": config.ci_integration,
            "fail_fast": config.fail_fast,
            "execution_timestamp": datetime.now().isoformat(),
        }

    def _format_detailed_issues(
        self,
        report: CompositeValidationReport,
        config: PreflightGovernanceConfig,
    ) -> list[JsonDict]:
        """Format issues for governance report."""
        all_issues = report.get_all_issues()
        return [self._format_issue(issue, config) for issue in all_issues]

    def _format_issue(
        self,
        issue: ValidationIssue,
        config: PreflightGovernanceConfig,
    ) -> JsonDict:
        """Format one issue for governance output."""
        return {
            "code": issue.code.value,
            "severity": issue.severity.value,
            "layer": issue.layer.value,
            "message": issue.message,
            "details": issue.details,
            "location": issue.location or "",
            "is_blocker": self._is_effective_blocker(issue),
            "governance_impact": self._determine_governance_impact(issue, config),
        }

    def _is_effective_blocker(self, issue: ValidationIssue) -> bool:
        """Determine if an issue is effectively a blocker after considering overrides."""
        if issue.severity != ValidationSeverity.BLOCKER:
            return False
        return issue.is_blocker()

    def _determine_governance_impact(
        self,
        issue: ValidationIssue,
        config: PreflightGovernanceConfig,
    ) -> str:
        """Determine governance impact of an issue."""
        if issue.is_blocker():
            if config.policy in _BLOCKING_POLICIES:
                return "execution_blocker"
            return "warning_with_blocker_severity"
        return "informational"

    def create_ci_gate_report(self, governance_report: JsonDict) -> JsonDict:
        """Create CI/CD gate compatible report."""
        decision = governance_report["execution_decision"]
        summary = governance_report["validation_summary"]

        return {
            "ci_gate": {
                "status": "PASS" if decision["execution_allowed"] else "FAIL",
                "reason": decision["reason"],
                "policy": governance_report["governance_metadata"]["policy"],
            },
            "metrics": {
                "total_issues": summary["total_issues"],
                "blockers": summary["total_blockers"],
                "warnings": summary["total_warnings"],
                "infos": summary["total_infos"],
            },
            "critical_issues": [
                issue
                for issue in governance_report["detailed_issues"]
                if issue["governance_impact"] == "execution_blocker"
            ],
        }
