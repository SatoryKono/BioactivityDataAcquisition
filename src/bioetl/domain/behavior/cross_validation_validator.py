"""Cross-validation governance service for composite pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from bioetl.domain.behavior.cross_validation_helpers import (
    _append_threshold_issue,
    _create_issue,
    _validate_coverage,
    _validate_pairs,
    _validate_rules,
)
from bioetl.domain.behavior.validation_result_envelopes import (
    build_validation_result,
)
from bioetl.domain.types import JsonDict
from bioetl.domain.types.validation_result import ValidationIssue, ValidationResult
from bioetl.domain.types.validation_severity import (
    IssueCode,
    ValidationLayer,
    ValidationSeverity,
)


class CrossValidationDispositionPolicy(StrEnum):
    """Runtime disposition semantics for cross-validation outcomes."""

    WARNING_ONLY = "warning_only"
    QUARANTINE = "quarantine"
    FAIL = "fail"


@dataclass(frozen=True)
class CrossValidationConfig:
    """Configuration for cross-validation governance."""

    pairs: list[dict[str, object]]
    rules: dict[str, str]
    strict_mode: bool = True
    coverage_threshold: float | None = None
    consistency_threshold: float | None = None
    disposition_policy: CrossValidationDispositionPolicy = (
        CrossValidationDispositionPolicy.FAIL
    )


class CrossValidationValidator:
    """Service for validating cross-validation configurations."""

    def validate_cross_validation_config(
        self,
        config: CrossValidationConfig,
        source_names: list[str],
        execution_context: JsonDict | None = None,
    ) -> ValidationResult:
        """Validate cross-source comparison rules before runtime execution."""
        issues = _collect_validation_issues(config, source_names)
        result: ValidationResult = build_validation_result(
            issues=issues,
            validation_layer=ValidationLayer.DEEP_PREFLIGHT,
            execution_context=execution_context or {},
        )
        return result

    def apply_disposition(
        self,
        validation_result: ValidationResult,
        config: CrossValidationConfig,
        runtime_context: JsonDict | None = None,
    ) -> ValidationResult:
        """Project blocker issues onto the configured runtime disposition policy."""
        issues = _apply_disposition_policy(
            issues=validation_result.issues,
            policy=config.disposition_policy,
        )
        if issues == validation_result.issues and runtime_context is None:
            return validation_result
        result: ValidationResult = build_validation_result(
            issues=issues,
            validation_layer=validation_result.validation_layer,
            execution_context=runtime_context or validation_result.execution_context,
            timestamp=validation_result.timestamp,
        )
        return result


def _collect_validation_issues(
    config: CrossValidationConfig,
    source_names: list[str],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = _validate_pairs(config.pairs, source_names)
    issues.extend(_validate_rules(config.rules))
    _append_threshold_issue(
        issues=issues,
        value=config.coverage_threshold,
        code=IssueCode.CMP_PF_CV_011,
        label="Coverage",
        field_name="coverage_threshold",
    )
    _append_threshold_issue(
        issues=issues,
        value=config.consistency_threshold,
        code=IssueCode.CMP_PF_CV_012,
        label="Consistency",
        field_name="consistency_threshold",
    )
    if config.strict_mode and not any(
        issue.severity == ValidationSeverity.BLOCKER for issue in issues
    ):
        issues.extend(_validate_coverage(config.pairs, source_names))
    return issues


def _apply_disposition_policy(
    *,
    issues: list[ValidationIssue],
    policy: CrossValidationDispositionPolicy,
) -> list[ValidationIssue]:
    """Apply disposition policy while preserving original issue order.

    Non-blocker issues pass through unchanged; blockers are rewritten in place.
    """
    if not issues:
        return issues

    return [
        (
            _apply_policy_to_issue(issue, policy)
            if issue.severity == ValidationSeverity.BLOCKER
            else issue
        )
        for issue in issues
    ]


def _collect_blocker_issues(issues: list[ValidationIssue]) -> list[ValidationIssue]:
    return [issue for issue in issues if issue.severity == ValidationSeverity.BLOCKER]


def _apply_policy_to_issue(
    issue: ValidationIssue,
    policy: CrossValidationDispositionPolicy,
) -> ValidationIssue:
    if policy == CrossValidationDispositionPolicy.WARNING_ONLY:
        return _build_disposed_issue(
            issue=issue,
            severity=ValidationSeverity.WARNING,
            suffix="downgraded from blocker by WARNING_ONLY policy",
            extra_details={
                "original_severity": "blocker",
                "disposition": "downgraded",
            },
        )
    if policy == CrossValidationDispositionPolicy.QUARANTINE:
        return _build_disposed_issue(
            issue=issue,
            severity=ValidationSeverity.BLOCKER,
            suffix="quarantined",
            extra_details={
                "disposition": "quarantined",
                "quarantine_reason": "cross_validation_failure",
            },
        )
    return _build_disposed_issue(
        issue=issue,
        severity=ValidationSeverity.BLOCKER,
        suffix="will fail execution",
        extra_details={"disposition": "fail", "execution_blocked": True},
    )


def _build_disposed_issue(
    *,
    issue: ValidationIssue,
    severity: ValidationSeverity,
    suffix: str,
    extra_details: JsonDict,
) -> ValidationIssue:
    issue_result: ValidationIssue = _create_issue(
        code=issue.code,
        severity=severity,
        message=f"{issue.message} ({suffix})",
        details={**(issue.details or {}), **extra_details},
        location=issue.location,
    )
    return issue_result
