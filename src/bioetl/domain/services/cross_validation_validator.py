"""Cross-validation governance service for composite pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from bioetl.domain.types import JsonDict
from bioetl.domain.types.validation_result import ValidationIssue, ValidationResult
from bioetl.domain.types.validation_severity import (
    IssueCode,
    ValidationLayer,
    ValidationSeverity,
)
from bioetl.domain.services.cross_validation_helpers import (
    _append_threshold_issue,
    _collect_covered_sources,
    _create_issue,
    _has_blocking_issues,
    _normalize_comparison_sources,
    _validate_coverage,
    _validate_pairs,
    _validate_rules,
)

_SUPPORTED_RULE_TYPES = {"strict", "lenient", "warn", "custom"}


class CrossValidationDispositionPolicy(StrEnum):
    """Runtime disposition semantics for cross-validation outcomes."""
    WARNING_ONLY = "warning_only"
    QUARANTINE = "quarantine"
    FAIL = "fail"


@dataclass(frozen=True)
class CrossValidationConfig:
    """Configuration for cross-validation governance."""

    pairs: list[dict]
    rules: dict[str, str]
    strict_mode: bool = True
    coverage_threshold: float | None = None
    consistency_threshold: float | None = None
    disposition_policy: CrossValidationDispositionPolicy = CrossValidationDispositionPolicy.FAIL


class CrossValidationValidator:
    """Service for validating cross-validation configurations."""

    def validate_cross_validation_config(
        self,
        config: CrossValidationConfig,
        source_names: list[str],
        execution_context: JsonDict | None = None,
    ) -> ValidationResult:
        issues = _validate_pairs(config.pairs, source_names)
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
        if config.strict_mode and not _has_blocking_issues(issues):
            issues.extend(_validate_coverage(config.pairs, source_names))
        return ValidationResult(
            issues=issues,
            validation_layer=ValidationLayer.DEEP_PREFLIGHT,
            execution_context=execution_context or {},
        )

    def apply_disposition(
        self,
        validation_result: ValidationResult,
        config: CrossValidationConfig,
        runtime_context: JsonDict | None = None,
    ) -> ValidationResult:
        """Apply disposition policy to validation result.
        
        Args:
            validation_result: Validation result from cross-validation
            config: Cross-validation configuration with disposition policy
            runtime_context: Optional runtime context for disposition decisions
            
        Returns:
            Validation result with disposition applied according to policy
        """
        if not validation_result.issues:
            return validation_result
        
        # Apply disposition based on policy
        disposed_issues = []
        for issue in validation_result.issues:
            if issue.severity == ValidationSeverity.BLOCKER:
                # Blockers are always applied according to disposition policy
                if config.disposition_policy == CrossValidationDispositionPolicy.WARNING_ONLY:
                    # Downgrade blocker to warning
                    disposed_issues.append(
                        _create_issue(
                            code=issue.code,
                            severity=ValidationSeverity.WARNING,
                            message=f"{issue.message} (downgraded from blocker by WARNING_ONLY policy)",
                            details={**issue.details, "original_severity": "blocker", "disposition": "downgraded"},
                        )
                    )
                elif config.disposition_policy == CrossValidationDispositionPolicy.QUARANTINE:
                    # Keep as blocker but add quarantine metadata
                    disposed_issues.append(
                        _create_issue(
                            code=issue.code,
                            severity=ValidationSeverity.BLOCKER,
                            message=f"{issue.message} (quarantined)",
                            details={**issue.details, "disposition": "quarantined", "quarantine_reason": "cross_validation_failure"},
                        )
                    )
                else:  # FAIL policy
                    # Keep as blocker with fail metadata
                    disposed_issues.append(
                        _create_issue(
                            code=issue.code,
                            severity=ValidationSeverity.BLOCKER,
                            message=f"{issue.message} (will fail execution)",
                            details={**issue.details, "disposition": "fail", "execution_blocked": True},
                        )
                    )
            else:
                # Non-blockers are passed through
                disposed_issues.append(issue)
        
        return ValidationResult(
            issues=disposed_issues,
            validation_layer=validation_result.validation_layer,
            execution_context=runtime_context or validation_result.execution_context,
            timestamp=validation_result.timestamp,
        )


def create_cross_validation_validator() -> CrossValidationValidator:
    """Factory function for CrossValidationValidator."""
    return CrossValidationValidator()
