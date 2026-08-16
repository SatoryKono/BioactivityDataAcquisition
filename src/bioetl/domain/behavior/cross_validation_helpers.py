"""Helper functions for cross-validation validation."""

from __future__ import annotations

from typing import cast

from bioetl.domain.behavior.cross_validation_source_helpers import (
    comparison_source_list as _comparison_source_list,
)
from bioetl.domain.types import JsonDict
from bioetl.domain.types.validation_result import ValidationIssue
from bioetl.domain.types.validation_severity import (
    IssueCode,
    ValidationLayer,
    ValidationSeverity,
)

_SUPPORTED_RULE_TYPES = frozenset({"strict", "lenient", "warn", "custom"})


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
        layer=ValidationLayer.DEEP_PREFLIGHT,
        message=message,
        details=details or {},
        location=location,
    )


def _validate_pairs(
    pairs: list[dict[str, object]], source_names: list[str]
) -> list[ValidationIssue]:
    if not pairs:
        return [
            _create_issue(
                IssueCode.CMP_PF_CV_002,
                ValidationSeverity.BLOCKER,
                "Cross-validation pairs cannot be empty",
                {"pairs": pairs},
            )
        ]

    valid_sources = set(source_names)
    issues: list[ValidationIssue] = []
    for index, pair in enumerate(pairs):
        issues.extend(_validate_single_pair(pair, index, valid_sources))
    return issues


def _validate_single_pair(
    pair: object,
    index: int,
    valid_sources: set[str],
) -> list[ValidationIssue]:
    shape_issue = _validate_pair_shape(pair, index)
    if shape_issue is not None:
        return [shape_issue]

    pair_mapping = cast("dict[object, object]", pair)
    source_name, comparison_sources = next(iter(pair_mapping.items()))
    normalized_sources, type_issue = _normalize_comparison_sources(
        source_name=source_name,
        comparison_sources=comparison_sources,
    )
    issues = _validate_source_name(source_name, index, valid_sources)
    if type_issue is not None:
        issues.append(type_issue)
        return issues
    if not normalized_sources:
        issues.append(
            _create_issue(
                IssueCode.CMP_PF_CV_006,
                ValidationSeverity.BLOCKER,
                f"Comparison sources for '{source_name}' cannot be empty",
                {"source_name": source_name, "comparison_sources": comparison_sources},
            )
        )
        return issues

    issues.extend(
        _validate_comparison_sources(
            comparison_sources=normalized_sources,
            source_name=source_name,
            valid_sources=valid_sources,
        )
    )
    return issues


def _validate_pair_shape(pair: object, index: int) -> ValidationIssue | None:
    if not isinstance(pair, dict):
        return _create_issue(
            IssueCode.CMP_PF_CV_003,
            ValidationSeverity.BLOCKER,
            f"Cross-validation pair {index} must be a dictionary",
            {"pair": pair, "index": index},
        )
    if len(pair) != 1:
        return _create_issue(
            IssueCode.CMP_PF_CV_004,
            ValidationSeverity.BLOCKER,
            f"Cross-validation pair {index} must have exactly one source mapping",
            {"pair": pair, "index": index},
        )
    return None


def _validate_source_name(
    source_name: object,
    index: int,
    valid_sources: set[str],
) -> list[ValidationIssue]:
    if not isinstance(source_name, str):
        return [
            _create_issue(
                IssueCode.CMP_PF_CV_005,
                ValidationSeverity.BLOCKER,
                f"Cross-validation source at index {index} must be a string",
                {"source_name": source_name, "index": index},
            )
        ]
    if source_name in valid_sources:
        return []
    return [
        _create_issue(
            IssueCode.CMP_PF_CV_005,
            ValidationSeverity.BLOCKER,
            f"Cross-validation source '{source_name}' not found in pipeline sources",
            {
                "source_name": source_name,
                "available_sources": sorted(valid_sources),
                "pair_index": index,
            },
        )
    ]


def _normalize_comparison_sources(
    *,
    source_name: object,
    comparison_sources: object,
) -> tuple[list[str], ValidationIssue | None]:
    if isinstance(comparison_sources, str):
        return [comparison_sources], None
    if isinstance(comparison_sources, list):
        if all(isinstance(item, str) for item in comparison_sources):
            return comparison_sources, None
        return [], _create_issue(
            IssueCode.CMP_PF_CV_006,
            ValidationSeverity.BLOCKER,
            f"Comparison sources for '{source_name}' must contain only strings",
            {"source_name": source_name, "comparison_sources": comparison_sources},
        )

    return [], _create_issue(
        IssueCode.CMP_PF_CV_006,
        ValidationSeverity.BLOCKER,
        f"Comparison sources for '{source_name}' must be string or list",
        {"source_name": source_name, "comparison_sources": comparison_sources},
    )


def _validate_comparison_sources(
    *,
    comparison_sources: list[str],
    source_name: object,
    valid_sources: set[str],
) -> list[ValidationIssue]:
    if _compares_only_to_self(source_name, comparison_sources):
        return [
            _create_issue(
                IssueCode.CMP_PF_CV_007,
                ValidationSeverity.BLOCKER,
                f"Cross-validation source '{source_name}' cannot compare only to itself",
                {
                    "comparison_source": source_name,
                    "source_name": source_name,
                    "available_sources": sorted(valid_sources),
                },
            )
        ]
    issues: list[ValidationIssue] = []
    for comparison_source in comparison_sources:
        if comparison_source == source_name:
            continue
        if comparison_source in valid_sources:
            continue
        issues.append(
            _create_issue(
                IssueCode.CMP_PF_CV_007,
                ValidationSeverity.BLOCKER,
                f"Comparison source '{comparison_source}' not found in pipeline sources",
                {
                    "comparison_source": comparison_source,
                    "source_name": source_name,
                    "available_sources": sorted(valid_sources),
                },
            )
        )
    return issues


def _compares_only_to_self(source_name: object, comparison_sources: list[str]) -> bool:
    if not isinstance(source_name, str):
        return False
    if not comparison_sources:
        return False
    return set(comparison_sources) == {source_name}


def _validate_rules(rules: dict[str, str]) -> list[ValidationIssue]:
    if not rules:
        return [
            _create_issue(
                IssueCode.CMP_PF_CV_008,
                ValidationSeverity.BLOCKER,
                "Cross-validation rules cannot be empty",
                {"rules": rules},
            )
        ]

    issues: list[ValidationIssue] = []
    for rule_name, rule_type in rules.items():
        issues.extend(_validate_single_rule(rule_name, rule_type))
    return issues


def _validate_single_rule(rule_name: str, rule_type: object) -> list[ValidationIssue]:
    if not isinstance(rule_type, str):
        return [
            _create_issue(
                IssueCode.CMP_PF_CV_009,
                ValidationSeverity.BLOCKER,
                f"Rule '{rule_name}' must be a string type, got {type(rule_type).__name__}",
                {"rule_name": rule_name, "rule_type": rule_type},
            )
        ]

    if rule_type in _SUPPORTED_RULE_TYPES:
        return []

    return [
        _create_issue(
            IssueCode.CMP_PF_CV_010,
            ValidationSeverity.BLOCKER,
            f"Unsupported cross-validation rule type '{rule_type}'",
            {"rule_name": rule_name, "rule_type": rule_type},
        )
    ]


def _append_threshold_issue(
    *,
    issues: list[ValidationIssue],
    value: object | None,
    code: IssueCode,
    label: str,
    field_name: str,
) -> None:
    if _is_valid_threshold(value):
        return
    issues.append(
        _create_issue(
            code,
            ValidationSeverity.BLOCKER,
            f"{label} threshold must be between 0.0 and 1.0",
            {field_name: value},
        )
    )


def _is_valid_threshold(value: object | None) -> bool:
    if value is None:
        return True
    # bool is a subclass of int — reject before numeric range checks.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return 0 <= value <= 1


def _validate_coverage(
    pairs: list[dict[str, object]],
    source_names: list[str],
) -> list[ValidationIssue]:
    if not source_names:
        return []

    covered_sources = _collect_covered_sources(pairs)
    uncovered_sources = set(source_names) - covered_sources
    if not uncovered_sources:
        return []

    return [
        _create_issue(
            IssueCode.CMP_PF_CV_013,
            ValidationSeverity.WARNING,
            f"Cross-validation does not cover all sources: {sorted(uncovered_sources)}",
            {
                "uncovered_sources": sorted(uncovered_sources),
                "covered_sources": sorted(covered_sources),
                "all_sources": sorted(source_names),
            },
        )
    ]


def _collect_covered_sources(pairs: list[dict[str, object]]) -> set[str]:
    covered_sources: set[str] = set()
    for pair in pairs:
        covered_sources.update(_covered_sources_from_pair(pair))
    return covered_sources


def _covered_sources_from_pair(pair: object) -> set[str]:
    if not isinstance(pair, dict):
        return set()
    covered_sources: set[str] = set()
    for source_name, comparison_sources in pair.items():
        covered_sources.update(_covered_source_names(source_name, comparison_sources))
    return covered_sources


def _covered_source_names(source_name: object, comparison_sources: object) -> set[str]:
    normalized = _comparison_source_list(comparison_sources)
    covered = {item for item in normalized if item != source_name}
    if not isinstance(source_name, str):
        return covered
    if not covered:
        return covered
    covered.add(source_name)
    return covered
