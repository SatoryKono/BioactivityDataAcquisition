"""Helper functions for composite validation."""

from __future__ import annotations

from bioetl.domain.behavior.aggregation_validator import AggregationConfig
from bioetl.domain.behavior.cross_validation_validator import CrossValidationConfig
from bioetl.domain.types import JsonDict
from bioetl.domain.types.validation_result import ValidationIssue
from bioetl.domain.types.validation_severity import (
    IssueCode,
    ValidationLayer,
    ValidationSeverity,
)


def _append_config_issue_if_invalid(
    *,
    issues: list[ValidationIssue],
    is_valid: bool,
    code: IssueCode,
    severity: ValidationSeverity,
    message: str,
    details: JsonDict | None = None,
) -> None:
    if is_valid:
        return
    issues.append(
        ValidationIssue(
            code=code,
            severity=severity,
            layer=ValidationLayer.DEEP_PREFLIGHT,
            message=message,
            details=details or {},
        )
    )


def _create_issue(
    code: IssueCode,
    severity: ValidationSeverity,
    message: str,
    details: JsonDict | None = None,
    location: str | None = None,
) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        severity=severity,
        layer=_get_layer_for_code(code),
        message=message,
        details=details or {},
        location=location,
    )


def _get_layer_for_code(code: IssueCode) -> ValidationLayer:
    if code.value.startswith("CMP-STR-"):
        return ValidationLayer.STRUCTURAL
    if code.value.startswith("CMP-PF-"):
        return ValidationLayer.DEEP_PREFLIGHT
    return ValidationLayer.RUNTIME_GUARD


def _convert_to_aggregation_config(config: JsonDict) -> AggregationConfig:
    return AggregationConfig(
        group_by=config.get("group_by", []),
        aggregations=config.get("aggregations", {}),
        source_field=config.get("source_field"),
        provenance_tracking=config.get("provenance_tracking", True),
    )


def _convert_to_cross_validation_config(config: JsonDict) -> CrossValidationConfig:
    return CrossValidationConfig(
        pairs=config.get("pairs", []),
        rules=config.get("rules", {}),
        strict_mode=config.get("strict_mode", True),
        coverage_threshold=config.get("coverage_threshold"),
        consistency_threshold=config.get("consistency_threshold"),
    )


def _is_valid_field_priorities(priorities: JsonDict) -> bool:
    """Reject missing priorities and duplicate priority ranks across fields."""
    seen_by_priority: dict[object, str] = {}
    for field, priority_config in priorities.items():
        priority = _extract_priority(priority_config)
        if priority is None:
            return False
        owner = seen_by_priority.get(priority)
        if owner is not None and owner != field:
            return False
        seen_by_priority[priority] = field
    return True


def _extract_priority(priority_config: object) -> object | None:
    if isinstance(priority_config, dict):
        return priority_config.get("priority")
    return None


def _is_valid_lineage_config(config: JsonDict) -> bool:
    return all(field in config for field in ("tracking_level", "source_fields"))
