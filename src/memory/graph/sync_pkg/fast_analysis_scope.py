"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import JsonValue
from memory.graph.sync_pkg.apply_verify import (
    CRITICAL_ANALYSIS_NODE_LABELS,
    CRITICAL_ANALYSIS_RELATION_TYPES,
)
from memory.graph.sync_pkg.critical_diff_issues import _critical_diff_issues
from memory.graph.sync_pkg.fast_analysis_snapshot_counts import _active_critical_names

__all__ = [
    "_critical_analysis_audit_issues",
    "_fast_analysis_scope",
]


def _fast_analysis_scope(
    snapshot_stats: dict[str, JsonValue],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return (
        _active_critical_names(snapshot_stats, "labels", CRITICAL_ANALYSIS_NODE_LABELS),
        _active_critical_names(
            snapshot_stats, "relation_types", CRITICAL_ANALYSIS_RELATION_TYPES
        ),
    )


def _critical_analysis_audit_issues(report: dict[str, JsonValue]) -> list[str]:
    issues: list[str] = []
    diff = report.get("diff", {})
    label_rows = diff.get("labels", []) if isinstance(diff, dict) else []
    relation_rows = diff.get("relation_types", []) if isinstance(diff, dict) else []

    issues.extend(
        _critical_diff_issues(label_rows, CRITICAL_ANALYSIS_NODE_LABELS, kind="label")
    )
    issues.extend(
        _critical_diff_issues(
            relation_rows, CRITICAL_ANALYSIS_RELATION_TYPES, kind="relation"
        )
    )
    return issues
