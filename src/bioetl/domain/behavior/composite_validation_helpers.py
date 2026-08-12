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
    """Convert a raw config dict into AggregationConfig.

    Raises:
        TypeError: When group_by or aggregations have invalid shapes.
        ValueError: When field values are semantically invalid.
    """
    group_by_raw = config.get("group_by", [])
    aggregations_raw = config.get("aggregations", {})
    if not isinstance(group_by_raw, list):
        raise TypeError(
            f"group_by must be a list of field names, got {type(group_by_raw).__name__}"
        )
    if not all(isinstance(item, str) for item in group_by_raw):
        raise TypeError("group_by entries must be strings")
    if not isinstance(aggregations_raw, dict):
        raise TypeError(
            "aggregations must be a mapping of field -> function, "
            f"got {type(aggregations_raw).__name__}"
        )
    for field_name, function in aggregations_raw.items():
        if not isinstance(field_name, str):
            raise TypeError("aggregations keys must be strings")
        if not isinstance(function, str):
            raise TypeError(
                f"aggregations[{field_name!r}] must be a string function name"
            )
    source_field = config.get("source_field")
    if source_field is not None and not isinstance(source_field, str):
        raise TypeError("source_field must be a string or null")
    provenance = config.get("provenance_tracking", True)
    if not isinstance(provenance, bool):
        raise TypeError("provenance_tracking must be a boolean")
    return AggregationConfig(
        group_by=list(group_by_raw),
        aggregations={str(k): str(v) for k, v in aggregations_raw.items()},
        source_field=source_field,
        provenance_tracking=provenance,
    )


def _convert_to_cross_validation_config(config: JsonDict) -> CrossValidationConfig:
    """Convert a raw config dict into CrossValidationConfig.

    Raises:
        TypeError: When pairs, rules, flags, or thresholds have invalid shapes.
        ValueError: When threshold values are out of range.
    """
    pairs_raw = config.get("pairs", [])
    rules_raw = config.get("rules", {})
    if not isinstance(pairs_raw, list):
        raise TypeError(f"pairs must be a list, got {type(pairs_raw).__name__}")
    if not all(isinstance(item, dict) for item in pairs_raw):
        raise TypeError("pairs entries must be dictionaries")
    if not isinstance(rules_raw, dict):
        raise TypeError(f"rules must be a mapping, got {type(rules_raw).__name__}")
    for rule_key, rule_value in rules_raw.items():
        if not isinstance(rule_key, str):
            raise TypeError("rules keys must be strings")
        if not isinstance(rule_value, str):
            raise TypeError(f"rules[{rule_key!r}] must be a string")
    strict_mode = config.get("strict_mode", True)
    if not isinstance(strict_mode, bool):
        raise TypeError("strict_mode must be a boolean")
    coverage = config.get("coverage_threshold")
    consistency = config.get("consistency_threshold")
    if coverage is not None and not isinstance(coverage, (int, float)):
        raise TypeError("coverage_threshold must be a number or null")
    if consistency is not None and not isinstance(consistency, (int, float)):
        raise TypeError("consistency_threshold must be a number or null")
    if coverage is not None and (coverage < 0 or coverage > 1):
        raise ValueError("coverage_threshold must be in [0, 1]")
    if consistency is not None and (consistency < 0 or consistency > 1):
        raise ValueError("consistency_threshold must be in [0, 1]")
    return CrossValidationConfig(
        pairs=list(pairs_raw),
        rules={str(k): str(v) for k, v in rules_raw.items()},
        strict_mode=strict_mode,
        coverage_threshold=float(coverage) if coverage is not None else None,
        consistency_threshold=float(consistency) if consistency is not None else None,
    )


def _is_valid_field_priorities(priorities: JsonDict) -> bool:
    """Reject missing priorities, unhashable ranks, and duplicate priority ranks."""
    seen_by_priority: dict[object, str] = {}
    for field, priority_config in priorities.items():
        priority = _extract_priority(priority_config)
        if priority is None:
            return False
        try:
            hash(priority)
        except TypeError:
            return False
        if priority in seen_by_priority:
            return False
        seen_by_priority[priority] = field
    return True


def _extract_priority(priority_config: object) -> object | None:
    if isinstance(priority_config, dict):
        return priority_config.get("priority")
    return None


def _is_valid_lineage_config(config: JsonDict) -> bool:
    return all(field in config for field in ("tracking_level", "source_fields"))
