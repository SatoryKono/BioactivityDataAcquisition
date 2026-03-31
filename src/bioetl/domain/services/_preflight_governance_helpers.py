"""Helpers for preflight governance policy and report shaping."""

from __future__ import annotations

from dataclasses import replace

from bioetl.domain.types import JsonDict
from bioetl.domain.types.validation_result import ValidationIssue, ValidationResult
from bioetl.domain.types.validation_severity import (
    ValidationLayer,
    ValidationSeverity,
)

from ._preflight_governance_types import GovernancePolicy, PreflightGovernanceConfig

BLOCKING_POLICIES: frozenset[GovernancePolicy] = frozenset(
    {
        GovernancePolicy.BLOCK_ON_ANY_ISSUE,
        GovernancePolicy.BLOCK_ON_BLOCKERS_ONLY,
        GovernancePolicy.CI_STRICT,
        GovernancePolicy.CI_RELAXED,
    }
)


def rebuild_validation_result(
    result: ValidationResult,
    *,
    layer: ValidationLayer,
    config: PreflightGovernanceConfig,
) -> ValidationResult:
    """Rebuild one validation result after applying issue overrides."""
    return ValidationResult(
        issues=apply_overrides_to_issues(result.issues, config),
        validation_layer=layer,
        execution_context=result.execution_context,
        timestamp=result.timestamp,
    )


def apply_overrides_to_issues(
    issues: list[ValidationIssue],
    config: PreflightGovernanceConfig,
) -> list[ValidationIssue]:
    """Apply severity overrides to individual issues."""
    if not config.issue_code_overrides:
        return issues
    overridden_issues: list[ValidationIssue] = []
    for issue in issues:
        override = config.issue_code_overrides.get(issue.code.value)
        overridden_issues.append(apply_issue_override(issue, override))
    return overridden_issues


def apply_issue_override(
    issue: ValidationIssue,
    override: ValidationSeverity | None,
) -> ValidationIssue:
    """Return issue with overridden severity when configuration requires it."""
    if override is None:
        return issue
    return replace(issue, severity=override)


def resolve_policy_block_state(
    *,
    report_has_any_issues: bool,
    has_effective_blockers: bool,
    policy: GovernancePolicy,
) -> tuple[bool, str]:
    """Resolve whether a policy blocks execution and why."""
    checks: dict[GovernancePolicy, tuple[bool, str]] = {
        GovernancePolicy.BLOCK_ON_ANY_ISSUE: (
            report_has_any_issues,
            "any_issue_found",
        ),
        GovernancePolicy.BLOCK_ON_BLOCKERS_ONLY: (
            has_effective_blockers,
            "blocker_issues_found",
        ),
        GovernancePolicy.CI_STRICT: (
            report_has_any_issues,
            "ci_strict_mode_violation",
        ),
        GovernancePolicy.CI_RELAXED: (
            has_effective_blockers,
            "ci_relaxed_blockers_found",
        ),
    }
    return checks.get(policy, (False, "no_blocking_issues"))


def build_governance_metadata(
    config: PreflightGovernanceConfig,
    *,
    execution_timestamp: str,
) -> JsonDict:
    """Build governance metadata for reporting."""
    return {
        "policy": config.policy.value,
        "ci_integration": config.ci_integration,
        "fail_fast": config.fail_fast,
        "execution_timestamp": execution_timestamp,
    }


def determine_governance_impact(
    *,
    issue: ValidationIssue,
    config: PreflightGovernanceConfig,
) -> str:
    """Determine governance impact of an issue."""
    if issue.is_blocker():
        if config.policy in BLOCKING_POLICIES:
            return "execution_blocker"
        return "warning_with_blocker_severity"
    return "informational"


def format_issue(
    *,
    issue: ValidationIssue,
    config: PreflightGovernanceConfig,
    is_effective_blocker: bool,
) -> JsonDict:
    """Format one issue for governance output."""
    return {
        "code": issue.code.value,
        "severity": issue.severity.value,
        "layer": issue.layer.value,
        "message": issue.message,
        "details": issue.details,
        "location": issue.location or "",
        "is_blocker": is_effective_blocker,
        "governance_impact": determine_governance_impact(issue=issue, config=config),
    }
