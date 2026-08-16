"""Helper functions for composite validation."""

from __future__ import annotations

from typing import cast

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
    return AggregationConfig(
        group_by=_aggregation_group_by(config.get("group_by", [])),
        aggregations=_aggregation_mapping(config.get("aggregations", {})),
        source_field=_optional_string(config.get("source_field"), "source_field"),
        provenance_tracking=_require_bool(
            config.get("provenance_tracking", True),
            "provenance_tracking",
        ),
    )


def _convert_to_cross_validation_config(config: JsonDict) -> CrossValidationConfig:
    """Convert a raw config dict into CrossValidationConfig.

    Raises:
        TypeError: When pairs, rules, flags, or thresholds have invalid shapes.
        ValueError: When threshold values are out of range.
    """
    return CrossValidationConfig(
        pairs=_cross_validation_pairs(config.get("pairs", [])),
        rules=_string_rules(config.get("rules", {})),
        strict_mode=_require_bool(config.get("strict_mode", True), "strict_mode"),
        coverage_threshold=_optional_unit_interval(
            config.get("coverage_threshold"),
            "coverage_threshold",
        ),
        consistency_threshold=_optional_unit_interval(
            config.get("consistency_threshold"),
            "consistency_threshold",
        ),
    )


def _aggregation_group_by(value: object) -> list[str]:
    """Validate and copy aggregation group-by fields."""
    if not isinstance(value, list):
        raise TypeError(
            f"group_by must be a list of field names, got {type(value).__name__}"
        )
    if not all(isinstance(item, str) for item in value):
        raise TypeError("group_by entries must be strings")
    return list(cast(list[str], value))


def _aggregation_mapping(value: object) -> dict[str, str]:
    """Validate and copy aggregation field/function entries."""
    if not isinstance(value, dict):
        raise TypeError(
            "aggregations must be a mapping of field -> function, "
            f"got {type(value).__name__}"
        )
    entries = (_aggregation_entry(field, function) for field, function in value.items())
    return dict(entries)


def _aggregation_entry(field: object, function: object) -> tuple[str, str]:
    """Validate one aggregation mapping entry."""
    if not isinstance(field, str):
        raise TypeError("aggregations keys must be strings")
    if not isinstance(function, str):
        raise TypeError(f"aggregations[{field!r}] must be a string function name")
    return field, function


def _optional_string(value: object, field_name: str) -> str | None:
    """Validate an optional string field."""
    if value is not None and not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string or null")
    return value


def _require_bool(value: object, field_name: str) -> bool:
    """Validate a required boolean field."""
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be a boolean")
    return value


def _cross_validation_pairs(value: object) -> list[dict[str, object]]:
    """Validate and copy cross-validation pair definitions."""
    if not isinstance(value, list) or not all(
        isinstance(item, dict) for item in value
    ):
        raise TypeError(
            f"pairs must be a list of dictionaries, got {type(value).__name__}"
        )
    return list(cast(list[dict[str, object]], value))


def _string_rules(value: object) -> dict[str, str]:
    """Validate and copy string-to-string cross-validation rules."""
    if not isinstance(value, dict):
        raise TypeError(f"rules must be a mapping, got {type(value).__name__}")
    if not all(
        isinstance(key, str) and isinstance(item, str)
        for key, item in value.items()
    ):
        raise TypeError("rules keys and values must be strings")
    return cast(dict[str, str], dict(value))


def _optional_unit_interval(value: object, field_name: str) -> float | None:
    """Validate an optional numeric threshold in the inclusive unit interval."""
    if value is None:
        return None
    if not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a number or null")
    if value < 0 or value > 1:
        raise ValueError(f"{field_name} must be in [0, 1]")
    return float(value)


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
