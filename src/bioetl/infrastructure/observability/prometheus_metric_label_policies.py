"""Label policy helpers for PrometheusMetrics."""

from __future__ import annotations

from bioetl.domain.observability_contract import normalize_observability_metric_labels
from bioetl.domain.ports import MetricLabels

OBSERVABILITY_EVENTS_COUNTER_NAME = "observability_events_total"

_ALLOWED_REASON_LABELS = frozenset(
    {
        "cross_validation",
        "filtered_out_silver",
        "data_quality",
        "schema_validation",
        "transform_error",
        "validation_error",
        "other",
    }
)
_ALLOWED_STAGE_LABELS = frozenset(
    {
        "validation",
        "threshold",
        "transform",
        "silver",
        "gold",
        "postrun",
        "other",
    }
)
_ALLOWED_SEVERITY_LABELS = frozenset(
    {"soft_fail", "hard_fail", "warning", "error", "other"}
)


def normalize_metric_dispatch_labels(
    name: str,
    labels: MetricLabels,
) -> MetricLabels:
    """Normalize metric labels for metrics with stricter label contracts."""
    if name == OBSERVABILITY_EVENTS_COUNTER_NAME:
        return normalize_observability_metric_labels(labels)
    return labels


def normalize_quarantine_reason(reason: str) -> str:
    """Normalize quarantine reason to a bounded label set."""
    return _normalize_bounded_label(reason, _ALLOWED_REASON_LABELS)


def normalize_dq_stage(stage: str) -> str:
    """Normalize DQ stage label to a bounded label set."""
    return _normalize_bounded_label(stage, _ALLOWED_STAGE_LABELS)


def normalize_dq_severity(severity: str) -> str:
    """Normalize DQ severity label to a bounded label set."""
    return _normalize_bounded_label(severity, _ALLOWED_SEVERITY_LABELS)


def _normalize_bounded_label(value: str, allowed_values: frozenset[str]) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    return normalized if normalized in allowed_values else "other"
