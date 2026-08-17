"""Normalize and validate cross-validation source payloads."""

from __future__ import annotations

from bioetl.domain.types import JsonDict
from bioetl.domain.types.validation_result import ValidationIssue
from bioetl.domain.types.validation_severity import (
    IssueCode,
    ValidationLayer,
    ValidationSeverity,
)


def create_cross_validation_issue(
    code: IssueCode,
    severity: ValidationSeverity,
    message: str,
    details: JsonDict | None = None,
    location: str | None = None,
) -> ValidationIssue:
    """Build a deep-preflight cross-validation issue."""
    return ValidationIssue(
        code=code,
        severity=severity,
        layer=ValidationLayer.DEEP_PREFLIGHT,
        message=message,
        details=details or {},
        location=location,
    )


def comparison_source_list(comparison_sources: object) -> list[str]:
    """Return only supported source-name strings from one serialized value."""
    if isinstance(comparison_sources, str):
        return [comparison_sources]
    if isinstance(comparison_sources, list):
        return [item for item in comparison_sources if isinstance(item, str)]
    return []


def validate_source_name(
    source_name: object,
    index: int,
    valid_sources: set[str],
) -> list[ValidationIssue]:
    """Validate one pair source against the configured source set."""
    if not isinstance(source_name, str):
        return [
            create_cross_validation_issue(
                IssueCode.CMP_PF_CV_005,
                ValidationSeverity.BLOCKER,
                f"Cross-validation source at index {index} must be a string",
                {"source_name": source_name, "index": index},
            )
        ]
    if source_name in valid_sources:
        return []
    return [
        create_cross_validation_issue(
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


def normalize_comparison_sources(
    *,
    source_name: object,
    comparison_sources: object,
) -> tuple[list[str], ValidationIssue | None]:
    """Normalize the comparison side of one source pair."""
    if isinstance(comparison_sources, str):
        return [comparison_sources], None
    if isinstance(comparison_sources, list):
        if all(isinstance(item, str) for item in comparison_sources):
            return comparison_sources, None
        return [], create_cross_validation_issue(
            IssueCode.CMP_PF_CV_006,
            ValidationSeverity.BLOCKER,
            f"Comparison sources for '{source_name}' must contain only strings",
            {"source_name": source_name, "comparison_sources": comparison_sources},
        )
    return [], create_cross_validation_issue(
        IssueCode.CMP_PF_CV_006,
        ValidationSeverity.BLOCKER,
        f"Comparison sources for '{source_name}' must be string or list",
        {"source_name": source_name, "comparison_sources": comparison_sources},
    )


def validate_comparison_sources(
    *,
    comparison_sources: list[str],
    source_name: object,
    valid_sources: set[str],
) -> list[ValidationIssue]:
    """Validate comparison targets for one source pair."""
    if is_self_only_comparison(comparison_sources, source_name):
        comparison_source = comparison_sources[0]
        return [
            create_cross_validation_issue(
                IssueCode.CMP_PF_CV_007,
                ValidationSeverity.BLOCKER,
                f"Comparison source '{comparison_source}' cannot compare to itself",
                {
                    "comparison_source": comparison_source,
                    "source_name": source_name,
                },
            )
        ]
    return [
        unknown_comparison_source_issue(comparison_source, source_name, valid_sources)
        for comparison_source in comparison_sources
        if comparison_source != source_name and comparison_source not in valid_sources
    ]


def is_self_only_comparison(comparison_sources: list[str], source_name: object) -> bool:
    """Return whether all configured targets point back to the source."""
    return bool(comparison_sources) and set(comparison_sources) == {source_name}


def unknown_comparison_source_issue(
    comparison_source: str,
    source_name: object,
    valid_sources: set[str],
) -> ValidationIssue:
    """Build the issue for an unknown comparison target."""
    return create_cross_validation_issue(
        IssueCode.CMP_PF_CV_007,
        ValidationSeverity.BLOCKER,
        f"Comparison source '{comparison_source}' not found in pipeline sources",
        {
            "comparison_source": comparison_source,
            "source_name": source_name,
            "available_sources": sorted(valid_sources),
        },
    )


def compares_only_to_self(source_name: object, comparison_sources: list[str]) -> bool:
    """Return whether a valid source name has only self-targets."""
    return (
        isinstance(source_name, str)
        and bool(comparison_sources)
        and set(comparison_sources) == {source_name}
    )
