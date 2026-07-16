"""Pipeline quality and structural policy Prometheus metrics."""

from __future__ import annotations

from prometheus_client import Counter

__all__ = [
    "DQ_CONTEXT_BUILD_FAILURES_TOTAL",
    "DQ_REPORT_GENERATED_TOTAL",
    "DQ_REPORT_SKIPPED_TOTAL",
    "DQ_SOFT_THRESHOLD_EXCEEDED",
    "STRUCTURAL_POLICY_EVENTS_TOTAL",
    "STRUCTURAL_POLICY_SHADOW_COMPARISONS_TOTAL",
]

STRUCTURAL_POLICY_EVENTS_TOTAL = Counter(
    "bioetl_structural_policy_events_total",
    "Total structural-policy events emitted by transformer structural enforcement",
    ["provider", "entity_type", "action"],
)

STRUCTURAL_POLICY_SHADOW_COMPARISONS_TOTAL = Counter(
    "bioetl_structural_policy_shadow_comparisons_total",
    "Total shadow comparisons between structural policy and semantic silver filters",
    ["provider", "entity_type", "comparison"],
)

DQ_SOFT_THRESHOLD_EXCEEDED = Counter(
    "bioetl_dq_soft_threshold_exceeded_total",
    "Total times DQ soft threshold was exceeded",
    ["pipeline"],
)

DQ_CONTEXT_BUILD_FAILURES_TOTAL = Counter(
    "bioetl_dq_context_build_failures_total",
    "Total failures while building DQ dataframe context for report generation",
    ["pipeline", "stage", "reason"],
)

DQ_REPORT_SKIPPED_TOTAL = Counter(
    "bioetl_dq_report_skipped_total",
    "Total DQ report generation skips by pipeline and medallion stage",
    ["pipeline", "stage", "reason"],
)

DQ_REPORT_GENERATED_TOTAL = Counter(
    "bioetl_dq_report_generated_total",
    "Total successfully generated DQ reports by pipeline and medallion stage",
    ["pipeline", "stage"],
)
