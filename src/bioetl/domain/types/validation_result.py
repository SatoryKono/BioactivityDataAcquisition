"""Validation result types for composite pipeline execution."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.types import JsonDict
from bioetl.domain.types.validation_severity import (
    IssueCode,
    ValidationLayer,
    ValidationSeverity,
)


@dataclass(frozen=True)
class ValidationIssue:
    """Single validation issue with full context."""

    code: IssueCode
    severity: ValidationSeverity
    layer: ValidationLayer
    message: str
    details: JsonDict | None = None
    location: str | None = None

    def is_blocker(self) -> bool:
        """Return True if this issue blocks execution."""
        if (
            isinstance(self.details, dict)
            and self.details.get("disposition") == "downgraded"
        ):
            return False
        return self.severity == ValidationSeverity.BLOCKER or self.code.is_blocker()


@dataclass(frozen=True)
class ValidationResult:
    """Complete validation result with issues and metadata."""

    issues: list[ValidationIssue]
    validation_layer: ValidationLayer
    execution_context: JsonDict | None = None
    timestamp: str | None = None

    def has_blockers(self) -> bool:
        """Return True if any blocker issues are present."""
        return any(issue.is_blocker() for issue in self.issues)

    def get_blockers(self) -> list[ValidationIssue]:
        """Return only blocker issues."""
        return [issue for issue in self.issues if issue.is_blocker()]

    def get_warnings(self) -> list[ValidationIssue]:
        """Return only warning issues."""
        return [
            issue
            for issue in self.issues
            if issue.severity == ValidationSeverity.WARNING
        ]

    def get_infos(self) -> list[ValidationIssue]:
        """Return only info issues."""
        return [
            issue for issue in self.issues if issue.severity == ValidationSeverity.INFO
        ]

    def is_valid(self) -> bool:
        """Return True if there are no blocker issues."""
        return not self.has_blockers()


@dataclass(frozen=True)
class CompositeValidationReport:
    """Aggregated validation report across all layers."""

    structural_result: ValidationResult
    deep_preflight_result: ValidationResult
    runtime_guard_result: ValidationResult | None = None
    execution_decision: JsonDict | None = None

    def has_any_issues(self) -> bool:
        """Return True when at least one issue exists in any layer."""
        return bool(self.get_all_issues())

    def has_any_blockers(self) -> bool:
        """Return True if any layer has blocker issues."""
        return (
            self.structural_result.has_blockers()
            or self.deep_preflight_result.has_blockers()
            or bool(
                self.runtime_guard_result and self.runtime_guard_result.has_blockers()
            )
        )

    def get_all_issues(self) -> list[ValidationIssue]:
        """Return all issues from all layers."""
        issues: list[ValidationIssue] = []
        issues.extend(self.structural_result.issues)
        issues.extend(self.deep_preflight_result.issues)
        if self.runtime_guard_result:
            issues.extend(self.runtime_guard_result.issues)
        return issues

    def get_all_warnings(self) -> list[ValidationIssue]:
        """Return all warning issues from all layers."""
        warnings: list[ValidationIssue] = []
        warnings.extend(self.structural_result.get_warnings())
        warnings.extend(self.deep_preflight_result.get_warnings())
        if self.runtime_guard_result:
            warnings.extend(self.runtime_guard_result.get_warnings())
        return warnings

    def get_all_infos(self) -> list[ValidationIssue]:
        """Return all informational issues from all layers."""
        infos: list[ValidationIssue] = []
        infos.extend(self.structural_result.get_infos())
        infos.extend(self.deep_preflight_result.get_infos())
        if self.runtime_guard_result:
            infos.extend(self.runtime_guard_result.get_infos())
        return infos

    def to_ci_format(self) -> JsonDict:
        """Convert to CI/CD compatible format."""
        runtime_guard_payload = self._runtime_guard_ci_payload()
        return {
            "validation_layers": {
                "structural": {
                    "issues": [
                        self._issue_to_dict(issue)
                        for issue in self.structural_result.issues
                    ],
                    "has_blockers": self.structural_result.has_blockers(),
                },
                "deep_preflight": {
                    "issues": [
                        self._issue_to_dict(issue)
                        for issue in self.deep_preflight_result.issues
                    ],
                    "has_blockers": self.deep_preflight_result.has_blockers(),
                },
                "runtime_guard": runtime_guard_payload,
            },
            "summary": {
                "total_issues": len(self.get_all_issues()),
                "total_blockers": len(self.get_all_blockers()),
                "execution_blocked": self.has_any_blockers(),
            },
        }

    def _runtime_guard_ci_payload(self) -> JsonDict:
        """Build CI payload section for runtime-guard validation."""
        if self.runtime_guard_result is None:
            return {"issues": [], "has_blockers": False}
        return {
            "issues": [
                self._issue_to_dict(issue) for issue in self.runtime_guard_result.issues
            ],
            "has_blockers": self.runtime_guard_result.has_blockers(),
        }

    def _issue_to_dict(self, issue: ValidationIssue) -> JsonDict:
        """Convert validation issue to dictionary."""
        return {
            "code": issue.code.value,
            "severity": issue.severity.value,
            "layer": issue.layer.value,
            "message": issue.message,
            "details": issue.details or {},
            "location": issue.location or "",
            "is_blocker": issue.is_blocker(),
        }

    def get_all_blockers(self) -> list[ValidationIssue]:
        """Return all blocker issues from all layers."""
        blockers: list[ValidationIssue] = []
        blockers.extend(self.structural_result.get_blockers())
        blockers.extend(self.deep_preflight_result.get_blockers())
        if self.runtime_guard_result:
            blockers.extend(self.runtime_guard_result.get_blockers())
        return blockers
