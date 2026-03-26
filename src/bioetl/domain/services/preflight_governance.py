"""Preflight governance service for composite execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

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
    ) -> JsonDict:
        """Apply governance policy to validation report."""
        execution_context = execution_context or {}
        report_with_overrides = self._apply_issue_overrides(validation_report)
        execution_decision = self._determine_execution_decision(report_with_overrides)
        return self._generate_governance_report(
            report_with_overrides, execution_decision, execution_context
        )

    def _apply_issue_overrides(
        self, report: CompositeValidationReport
    ) -> CompositeValidationReport:
        """Apply severity overrides from configuration."""
        if not self.config.issue_code_overrides:
            return report
        structural_issues = self._apply_overrides_to_issues(
            report.structural_result.issues
        )
        deep_issues = self._apply_overrides_to_issues(
            report.deep_preflight_result.issues
        )

        runtime_result = self._runtime_result_with_overrides(
            report.runtime_guard_result
        )

        return CompositeValidationReport(
            structural_result=ValidationResult(
                issues=structural_issues,
                validation_layer=ValidationLayer.STRUCTURAL,
                execution_context=report.structural_result.execution_context,
                timestamp=report.structural_result.timestamp,
            ),
            deep_preflight_result=ValidationResult(
                issues=deep_issues,
                validation_layer=ValidationLayer.DEEP_PREFLIGHT,
                execution_context=report.deep_preflight_result.execution_context,
                timestamp=report.deep_preflight_result.timestamp,
            ),
            runtime_guard_result=runtime_result,
        )

    def _runtime_result_with_overrides(
        self,
        runtime_result: ValidationResult | None,
    ) -> ValidationResult | None:
        """Apply overrides to runtime-guard result when present."""
        if runtime_result is None:
            return None
        return ValidationResult(
            issues=self._apply_overrides_to_issues(runtime_result.issues),
            validation_layer=ValidationLayer.RUNTIME_GUARD,
            execution_context=runtime_result.execution_context,
            timestamp=runtime_result.timestamp,
        )

    def _apply_overrides_to_issues(
        self, issues: list[ValidationIssue]
    ) -> list[ValidationIssue]:
        """Apply severity overrides to individual issues."""
        if not self.config.issue_code_overrides:
            return issues

        overridden_issues: list[ValidationIssue] = []
        for issue in issues:
            override = self.config.issue_code_overrides.get(issue.code.value)
            if override:
                overridden_issue = ValidationIssue(
                    code=issue.code,
                    severity=override,
                    layer=issue.layer,
                    message=issue.message,
                    details=issue.details,
                    location=issue.location,
                )
                overridden_issues.append(overridden_issue)
            else:
                overridden_issues.append(issue)

        return overridden_issues

    def _determine_execution_decision(
        self, report: CompositeValidationReport
    ) -> JsonDict:
        """Determine execution decision based on governance policy."""
        policy = self.config.policy
        if policy is GovernancePolicy.WARNING_ONLY:
            return {
                "execution_allowed": True,
                "reason": "warning_only_mode",
                "policy_applied": policy.value,
            }

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
        blocked, reason = checks.get(policy, (False, "no_blocking_issues"))
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

    def _generate_governance_report(
        self,
        report: CompositeValidationReport,
        execution_decision: JsonDict,
        execution_context: JsonDict,
    ) -> JsonDict:
        """Generate comprehensive governance report."""
        return {
            "governance_metadata": {
                "policy": self.config.policy.value,
                "ci_integration": self.config.ci_integration,
                "fail_fast": self.config.fail_fast,
                "execution_timestamp": datetime.now().isoformat(),
            },
            "execution_decision": execution_decision,
            "validation_summary": {
                "total_issues": len(report.get_all_issues()),
                "total_blockers": len(report.get_all_blockers()),
                "total_warnings": len(report.get_all_warnings()),
                "total_infos": len(report.get_all_infos()),
                "layers": {
                    "structural": {
                        "issues": len(report.structural_result.issues),
                        "blockers": len(report.structural_result.get_blockers()),
                    },
                    "deep_preflight": {
                        "issues": len(report.deep_preflight_result.issues),
                        "blockers": len(report.deep_preflight_result.get_blockers()),
                    },
                    "runtime_guard": {
                        "issues": (
                            len(report.runtime_guard_result.issues)
                            if report.runtime_guard_result
                            else 0
                        ),
                        "blockers": (
                            len(report.runtime_guard_result.get_blockers())
                            if report.runtime_guard_result
                            else 0
                        ),
                    },
                },
            },
            "execution_context": execution_context,
            "detailed_issues": self._format_detailed_issues(report),
        }

    def _format_detailed_issues(
        self,
        report: CompositeValidationReport,
    ) -> list[JsonDict]:
        """Format issues for governance report."""
        all_issues = report.get_all_issues()
        return [
            {
                "code": issue.code.value,
                "severity": issue.severity.value,
                "layer": issue.layer.value,
                "message": issue.message,
                "details": issue.details,
                "location": issue.location or "",
                "is_blocker": self._is_effective_blocker(issue),
                "governance_impact": self._determine_governance_impact(issue),
            }
            for issue in all_issues
        ]

    def _is_effective_blocker(self, issue: ValidationIssue) -> bool:
        """Determine if an issue is effectively a blocker after considering overrides."""
        if issue.severity != ValidationSeverity.BLOCKER:
            return False
        return issue.is_blocker()

    def _determine_governance_impact(self, issue: ValidationIssue) -> str:
        """Determine governance impact of an issue."""
        blocking_policies = {
            GovernancePolicy.BLOCK_ON_ANY_ISSUE,
            GovernancePolicy.BLOCK_ON_BLOCKERS_ONLY,
            GovernancePolicy.CI_STRICT,
            GovernancePolicy.CI_RELAXED,
        }
        if issue.is_blocker():
            if self.config.policy in blocking_policies:
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


def create_preflight_governance_service(
    config: PreflightGovernanceConfig | None = None,
) -> PreflightGovernanceService:
    """Factory function for PreflightGovernanceService."""
    return PreflightGovernanceService(config)
