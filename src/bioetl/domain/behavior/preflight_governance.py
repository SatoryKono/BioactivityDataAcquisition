"""Preflight governance evaluator for composite execution."""

from __future__ import annotations

__all__ = [
    "GovernancePolicy",
    "PreflightGovernanceConfig",
    "PreflightGovernor",
]

from bioetl.domain.behavior._preflight_governance_helpers import (
    build_governance_metadata,
    format_issue,
    rebuild_validation_result,
    resolve_policy_block_state,
)
from bioetl.domain.behavior._preflight_governance_types import (
    GovernancePolicy,
    PreflightGovernanceConfig,
)
from bioetl.domain.behavior.preflight_governance_reporting import (
    build_validation_summary,
)
from bioetl.domain.types import JsonDict
from bioetl.domain.types.validation_result import (
    CompositeValidationReport,
    ValidationIssue,
)
from bioetl.domain.types.validation_severity import ValidationLayer, ValidationSeverity


class PreflightGovernor:
    """Evaluator for preflight execution governance."""

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
            structural_result=rebuild_validation_result(
                report.structural_result,
                layer=ValidationLayer.STRUCTURAL,
                config=config,
            ),
            deep_preflight_result=rebuild_validation_result(
                report.deep_preflight_result,
                layer=ValidationLayer.DEEP_PREFLIGHT,
                config=config,
            ),
            runtime_guard_result=(
                rebuild_validation_result(
                    report.runtime_guard_result,
                    layer=ValidationLayer.RUNTIME_GUARD,
                    config=config,
                )
                if report.runtime_guard_result is not None
                else None
            ),
        )

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

        blocked, reason = resolve_policy_block_state(
            report_has_any_issues=report.has_any_issues(),
            has_effective_blockers=self._has_effective_blockers(report),
            policy=policy,
        )
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
        config: PreflightGovernanceConfig,
    ) -> JsonDict:
        """Generate comprehensive governance report."""
        return {
            "governance_metadata": build_governance_metadata(
                config,
                execution_timestamp=self._resolve_execution_timestamp(report),
            ),
            "execution_decision": execution_decision,
            "validation_summary": build_validation_summary(report),
            "execution_context": execution_context,
            "detailed_issues": self._format_detailed_issues(report, config),
        }

    @staticmethod
    def _resolve_execution_timestamp(report: CompositeValidationReport) -> str:
        """Resolve governance timestamp from existing validation results."""
        candidates = (
            report.runtime_guard_result,
            report.deep_preflight_result,
            report.structural_result,
        )
        for result in candidates:
            if result is not None and result.timestamp:
                timestamp: str = result.timestamp
                return timestamp
        return ""

    def _format_detailed_issues(
        self,
        report: CompositeValidationReport,
        config: PreflightGovernanceConfig,
    ) -> list[JsonDict]:
        """Format issues for governance report."""
        all_issues = report.get_all_issues()
        formatted_issues: list[JsonDict] = [
            self._format_issue(issue, config) for issue in all_issues
        ]
        return formatted_issues

    def _format_issue(
        self,
        issue: ValidationIssue,
        config: PreflightGovernanceConfig,
    ) -> JsonDict:
        """Format one issue for governance output."""
        return format_issue(
            issue=issue,
            config=config,
            is_effective_blocker=self._is_effective_blocker(issue),
        )

    def _is_effective_blocker(self, issue: ValidationIssue) -> bool:
        """Determine if an issue is effectively a blocker after considering overrides."""
        if issue.severity != ValidationSeverity.BLOCKER:
            return False
        is_blocker: bool = issue.is_blocker()
        return is_blocker

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
