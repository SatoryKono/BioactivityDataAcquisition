"""Unit tests for composite validation result value types."""

from __future__ import annotations

import pytest

from bioetl.domain.types.validation_result import (
    CompositeValidationReport,
    ValidationIssue,
    ValidationResult,
)
from bioetl.domain.types.validation_severity import (
    IssueCode,
    ValidationLayer,
    ValidationSeverity,
)

pytestmark = pytest.mark.unit


def _issue(
    code: IssueCode,
    severity: ValidationSeverity,
    *,
    details: dict[str, object] | None = None,
) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        severity=severity,
        layer=ValidationLayer.DEEP_PREFLIGHT,
        message=code.value,
        details=details,
        location="config.yaml",
    )


def test_validation_issue_blocker_respects_downgraded_disposition() -> None:
    blocker = _issue(IssueCode.CMP_PF_AGG_001, ValidationSeverity.BLOCKER)
    downgraded = _issue(
        IssueCode.CMP_PF_AGG_001,
        ValidationSeverity.BLOCKER,
        details={"disposition": "downgraded"},
    )
    warning = _issue(IssueCode.CMP_PF_FIELD_001, ValidationSeverity.WARNING)

    assert blocker.is_blocker()
    assert not downgraded.is_blocker()
    assert not warning.is_blocker()


def test_validation_result_filters_blockers_warnings_and_infos() -> None:
    blocker = _issue(IssueCode.CMP_PF_AGG_001, ValidationSeverity.BLOCKER)
    warning = _issue(IssueCode.CMP_PF_FIELD_001, ValidationSeverity.WARNING)
    info = _issue(IssueCode.CMP_PF_CV_013, ValidationSeverity.INFO)
    result = ValidationResult(
        issues=[blocker, warning, info],
        validation_layer=ValidationLayer.DEEP_PREFLIGHT,
        execution_context={"pipeline": "composite"},
        timestamp="2026-06-16T00:00:00Z",
    )

    assert result.has_blockers()
    assert result.get_blockers() == [blocker]
    assert result.get_warnings() == [warning]
    assert result.get_infos() == [info]
    assert result.is_valid() is False
    assert result.execution_context == {"pipeline": "composite"}


def test_composite_validation_report_aggregates_layers_and_ci_payload() -> None:
    structural_warning = ValidationResult(
        issues=[_issue(IssueCode.CMP_STR_CONFIG_002, ValidationSeverity.WARNING)],
        validation_layer=ValidationLayer.STRUCTURAL,
    )
    deep_blocker = ValidationResult(
        issues=[_issue(IssueCode.CMP_PF_AGG_001, ValidationSeverity.BLOCKER)],
        validation_layer=ValidationLayer.DEEP_PREFLIGHT,
    )
    runtime_info = ValidationResult(
        issues=[_issue(IssueCode.CMP_RT_GRAIN_001, ValidationSeverity.INFO)],
        validation_layer=ValidationLayer.RUNTIME_GUARD,
    )
    report = CompositeValidationReport(
        structural_result=structural_warning,
        deep_preflight_result=deep_blocker,
        runtime_guard_result=runtime_info,
        execution_decision={"execution_allowed": False},
    )

    assert report.has_any_issues()
    assert report.has_any_blockers()
    assert len(report.get_all_issues()) == 3
    assert len(report.get_all_blockers()) == 3
    assert len(report.get_all_warnings()) == 1
    assert len(report.get_all_infos()) == 1

    payload = report.to_ci_format()
    assert payload["summary"] == {
        "total_issues": 3,
        "total_blockers": 3,
        "execution_blocked": True,
    }
    assert payload["validation_layers"]["runtime_guard"]["has_blockers"] is True
    assert payload["validation_layers"]["deep_preflight"]["issues"][0]["location"] == (
        "config.yaml"
    )


def test_composite_validation_report_handles_missing_runtime_guard() -> None:
    report = CompositeValidationReport(
        structural_result=ValidationResult([], ValidationLayer.STRUCTURAL),
        deep_preflight_result=ValidationResult([], ValidationLayer.DEEP_PREFLIGHT),
    )

    assert not report.has_any_issues()
    assert not report.has_any_blockers()
    assert report.get_all_issues() == []
    assert report.get_all_warnings() == []
    assert report.get_all_infos() == []
    assert report.get_all_blockers() == []
    assert report.to_ci_format()["validation_layers"]["runtime_guard"] == {
        "issues": [],
        "has_blockers": False,
    }
