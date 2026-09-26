"""Helper functions for cross-validation validation."""

from __future__ import annotations

from typing import cast

from bioetl.domain.behavior.cross_validation_coverage import (
    collect_covered_sources as _collect_covered_sources,
)
from bioetl.domain.behavior.cross_validation_coverage import (
    validate_coverage as _validate_coverage,
)
from bioetl.domain.behavior.cross_validation_source_helpers import (
    comparison_source_list as _comparison_source_list,
)
from bioetl.domain.behavior.cross_validation_source_helpers import (
    create_cross_validation_issue,
)
from bioetl.domain.behavior.cross_validation_source_helpers import (
    normalize_comparison_sources as _normalize_comparison_sources,
)
from bioetl.domain.behavior.cross_validation_source_helpers import (
    validate_comparison_sources as _validate_comparison_sources,
)
from bioetl.domain.behavior.cross_validation_source_helpers import (
    validate_source_name as _validate_source_name,
)
from bioetl.domain.types.validation_result import ValidationIssue
from bioetl.domain.types.validation_severity import (
    IssueCode,
    ValidationSeverity,
)

__all__ = [
    "_collect_covered_sources",
    "_comparison_source_list",
    "_validate_coverage",
]

_SUPPORTED_RULE_TYPES = frozenset({"strict", "lenient", "warn", "custom"})
_create_issue = create_cross_validation_issue


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
