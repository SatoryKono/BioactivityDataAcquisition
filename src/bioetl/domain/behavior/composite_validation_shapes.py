"""Fail-closed shape checks for composite validation."""

from __future__ import annotations

from bioetl.domain.behavior.composite_validation_helpers import _create_issue
from bioetl.domain.behavior.validation_result_envelopes import build_validation_result
from bioetl.domain.types import JsonDict
from bioetl.domain.types.validation_result import ValidationIssue, ValidationResult
from bioetl.domain.types.validation_severity import (
    IssueCode,
    ValidationLayer,
    ValidationSeverity,
)


def build_structural_validation_result(
    *, pipeline_name: str, composite_config: object
) -> ValidationResult:
    """Build the structural result without probing malformed mappings."""
    issues: list[ValidationIssue] = []
    if not isinstance(composite_config, dict):
        issues.append(
            _create_issue(
                IssueCode.CMP_STR_SCHEMA_001,
                ValidationSeverity.BLOCKER,
                "Composite config must be a dictionary",
                {"actual_type": type(composite_config).__name__},
            )
        )
    else:
        issues.extend(
            _create_issue(
                IssueCode.CMP_STR_CONFIG_002,
                ValidationSeverity.BLOCKER,
                f"Missing required field: {field}",
                {"missing_field": field},
            )
            for field in ("sources", "merge_strategy", "output_schema")
            if field not in composite_config
        )
    return build_validation_result(
        issues=issues,
        validation_layer=ValidationLayer.STRUCTURAL,
        execution_context={"pipeline_name": pipeline_name},
    )


def as_output_schema(raw: object) -> tuple[JsonDict | None, list[ValidationIssue]]:
    """Accept only a mapping output schema."""
    if isinstance(raw, dict):
        return raw, []
    return None, [
        _create_issue(
            IssueCode.CMP_STR_SCHEMA_001,
            ValidationSeverity.BLOCKER,
            "output_schema must be a mapping",
            {"actual_type": type(raw).__name__},
        )
    ]


def as_source_names(raw: object) -> tuple[list[str] | None, list[ValidationIssue]]:
    """Accept only a list of source name strings."""
    if isinstance(raw, list) and all(isinstance(item, str) for item in raw):
        return list(raw), []
    return None, [
        _create_issue(
            IssueCode.CMP_STR_FORMAT_003,
            ValidationSeverity.BLOCKER,
            "sources must be a list of strings",
            {"actual_type": type(raw).__name__},
        )
    ]


def precheck_cross_validation_config(config: object) -> list[ValidationIssue]:
    """Reject malformed cross-validation sections before decoding."""
    if not isinstance(config, dict):
        return [
            _create_issue(
                IssueCode.CMP_PF_CV_002,
                ValidationSeverity.BLOCKER,
                "Cross-validation configuration must be a dictionary",
                {"actual_type": type(config).__name__},
            )
        ]
    rules = config.get("rules")
    if isinstance(rules, dict) and rules:
        return []
    return [
        _create_issue(
            IssueCode.CMP_PF_CV_008,
            ValidationSeverity.BLOCKER,
            "Cross-validation rules cannot be empty",
            {"rules": rules if isinstance(rules, dict) else {}},
        )
    ]
