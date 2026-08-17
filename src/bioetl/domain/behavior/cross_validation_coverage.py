"""Coverage analysis helpers for composite cross-validation."""

from __future__ import annotations

from bioetl.domain.behavior.cross_validation_source_helpers import (
    comparison_source_list,
)
from bioetl.domain.types.validation_result import ValidationIssue
from bioetl.domain.types.validation_severity import (
    IssueCode,
    ValidationLayer,
    ValidationSeverity,
)


def validate_coverage(
    pairs: list[dict[str, object]],
    source_names: list[str],
) -> list[ValidationIssue]:
    """Report source names that no valid cross-source comparison covers."""
    if not source_names:
        return []
    covered_sources = collect_covered_sources(pairs)
    uncovered_sources = set(source_names) - covered_sources
    if not uncovered_sources:
        return []
    return [
        ValidationIssue(
            code=IssueCode.CMP_PF_CV_013,
            severity=ValidationSeverity.WARNING,
            layer=ValidationLayer.DEEP_PREFLIGHT,
            message=(
                "Cross-validation does not cover all sources: "
                f"{sorted(uncovered_sources)}"
            ),
            details={
                "uncovered_sources": sorted(uncovered_sources),
                "covered_sources": sorted(covered_sources),
                "all_sources": sorted(source_names),
            },
        )
    ]


def collect_covered_sources(pairs: list[dict[str, object]]) -> set[str]:
    """Return sources participating in at least one cross-source comparison."""
    covered_sources: set[str] = set()
    for pair in pairs:
        covered_sources.update(_covered_sources_for_pair(pair))
    return covered_sources


def _covered_sources_for_pair(pair: object) -> set[str]:
    if not isinstance(pair, dict):
        return set()
    covered_sources: set[str] = set()
    for source_name, comparison_sources in pair.items():
        covered_sources.update(
            _covered_sources_for_mapping(source_name, comparison_sources)
        )
    return covered_sources


def _covered_sources_for_mapping(
    source_name: object, comparison_sources: object
) -> set[str]:
    normalized_sources = comparison_source_list(comparison_sources)
    non_self_sources = {
        source for source in normalized_sources if source != source_name
    }
    source = (
        {source_name} if isinstance(source_name, str) and non_self_sources else set()
    )
    return source | non_self_sources
