"""Helper functions for cross-validation validation."""

from __future__ import annotations

from typing import Any

from bioetl.domain.types import JsonDict
from bioetl.domain.types.validation_result import IssueCode, ValidationIssue, ValidationLayer, ValidationSeverity


def _has_blocking_issues(issues: list[ValidationIssue]) -> bool:
    return any(issue.severity == ValidationSeverity.BLOCKER for issue in issues)


def _validate_pairs(pairs: list[dict], source_names: list[str]) -> list[ValidationIssue]:
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
    if not isinstance(pair, dict):
        return [
            _create_issue(
                IssueCode.CMP_PF_CV_003,
                ValidationSeverity.BLOCKER,
                f"Cross-validation pair {index} must be a dictionary",
                {"pair": pair, "index": index},
            )
        ]
    if len(pair) != 1:
        return [
            _create_issue(
                IssueCode.CMP_PF_CV_004,
                ValidationSeverity.BLOCKER,
                f"Cross-validation pair {index} must have exactly one source mapping",
                {"pair": pair, "index": index},
            )
        ]
    source_name, comparison_sources = next(iter(pair.items()))
    issues = _validate_source_name(source_name, index, valid_sources)
    normalized, type_issue = _normalize_comparison_sources(source_name, comparison_sources)
    if type_issue is not None:
        issues.append(type_issue)
    if not normalized:
        issues.append(
            _create_issue(
                IssueCode.CMP_PF_CV_005,
                ValidationSeverity.BLOCKER,
                f"Cross-validation pair {index} has no valid comparison sources",
                {"pair": pair, "index": index},
            )
        )
    else:
        issues.extend(_validate_comparison_sources(normalized, source_name))
    return issues


def _validate_source_name(
    source_name: object,
    index: int,
    valid_sources: set[str],
) -> list[ValidationIssue]:
    if not isinstance(source_name, str):
        return [
            _create_issue(
                IssueCode.CMP_PF_CV_001,
                ValidationSeverity.BLOCKER,
                f"Cross-validation source name {index} must be a string",
                {"source_name": source_name, "index": index},
            )
        ]
    if source_name not in valid_sources:
        return [
            _create_issue(
                IssueCode.CMP_PF_CV_007,
                ValidationSeverity.BLOCKER,
                f"Cross-validation source '{source_name}' not found in pipeline sources",
                {"source_name": source_name, "available_sources": sorted(valid_sources), "pair_index": index},
            )
        ]
    return []


def _normalize_comparison_sources(
    source_name: object,
    comparison_sources: object,
) -> tuple[list[str], ValidationIssue | None]:
    if isinstance(comparison_sources, str):
        return [comparison_sources], None
    if isinstance(comparison_sources, list):
        return [item for item in comparison_sources if isinstance(item, str)], None
    return [], _create_issue(
        IssueCode.CMP_PF_CV_006,
        ValidationSeverity.BLOCKER,
        f"Comparison sources for '{source_name}' must be string or list",
        {"source_name": source_name, "comparison_sources": comparison_sources},
    )


def _validate_comparison_sources(
    comparison_sources: list[str],
    source_name: object,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for comparison_source in comparison_sources:
        if comparison_source == source_name:
            issues.append(
                _create_issue(
                    IssueCode.CMP_PF_CV_008,
                    ValidationSeverity.BLOCKER,
                    f"Source '{source_name}' cannot compare against itself",
                    {"source_name": source_name, "comparison_source": comparison_source},
                )
            )
    return issues


def _validate_rules(rules: dict[str, str]) -> list[ValidationIssue]:
    if not rules:
        return [
            _create_issue(
                IssueCode.CMP_PF_CV_009,
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
    if not isinstance(rule_name, str):
        return [
            _create_issue(
                IssueCode.CMP_PF_CV_010,
                ValidationSeverity.BLOCKER,
                f"Rule name must be a string, got {type(rule_type).__name__}",
                {"rule_name": rule_name, "rule_type": rule_type},
            )
        ]
    if rule_type not in ("strict", "lenient", "custom"):
        return [
            _create_issue(
                IssueCode.CMP_PF_CV_011,
                ValidationSeverity.BLOCKER,
                f"Rule '{rule_name}' has invalid type '{rule_type}'",
                {"rule_name": rule_name, "rule_type": rule_type},
            )
        ]
    return []


def _append_threshold_issue(
    issues: list[ValidationIssue],
    value: Any,
    code: IssueCode,
    label: str,
    field_name: str,
) -> None:
    if value is not None and (not isinstance(value, (int, float)) or value < 0 or value > 1):
        issues.append(
            _create_issue(
                code,
                ValidationSeverity.BLOCKER,
                f"{label} threshold must be a number between 0 and 1",
                {field_name: value},
            )
        )


def _validate_coverage(
    pairs: list[dict],
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


def _collect_covered_sources(pairs: list[dict]) -> set[str]:
    covered_sources: set[str] = set()
    for pair in pairs:
        for source_name in pair.keys():
            covered_sources.add(source_name)
    return covered_sources


def _sources_from_pair(pair: object) -> set[str]:
    if isinstance(pair, dict):
        return set(pair.keys())
    return set()


def _comparison_source_list(comparison_sources: object) -> list[str]:
    if isinstance(comparison_sources, list):
        return [str(item) for item in comparison_sources if isinstance(item, str)]
    if isinstance(comparison_sources, str):
        return [comparison_sources]
    return []


def _create_issue(
    code: IssueCode,
    severity: ValidationSeverity,
    message: str,
    context: JsonDict,
) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        severity=severity,
        message=message,
        details=context,
        layer=ValidationLayer.DEEP_PREFLIGHT,
    )