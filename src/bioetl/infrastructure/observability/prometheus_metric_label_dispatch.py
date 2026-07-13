"""Metric label normalization dispatch for Prometheus metrics."""

from __future__ import annotations

from bioetl.domain.observability_contract import (
    normalize_observability_metric_labels,
    normalize_observability_pipeline_label,
)
from bioetl.domain.ports import MetricLabels
from bioetl.infrastructure.observability._prometheus_metric_label_dispatch_core import (
    normalize_group_metric_labels,
    validate_metric_label_policy,
)
from bioetl.infrastructure.observability._prometheus_metric_label_dispatch_policy import (
    normalize_policy_metric_labels,
)
from bioetl.infrastructure.observability._prometheus_metric_label_dispatch_publication import (
    normalize_publication_metric_labels,
)
from bioetl.infrastructure.observability.prometheus_metric_label_policy_sets import (
    OBSERVABILITY_EVENTS_COUNTER_NAME,
)

__all__ = ["normalize_metric_dispatch_labels", "validate_metric_label_policy"]


def _normalize_common_metric_labels(labels: MetricLabels) -> MetricLabels:
    if "pipeline" not in labels:
        return labels
    return {
        **labels,
        "pipeline": normalize_observability_pipeline_label(labels.get("pipeline")),
    }


def normalize_metric_dispatch_labels(
    name: str,
    labels: MetricLabels,
) -> MetricLabels:
    """Normalize metric labels for metrics with stricter label contracts."""
    validate_metric_label_policy(name, labels)
    if name == OBSERVABILITY_EVENTS_COUNTER_NAME:
        return _normalize_common_metric_labels(
            normalize_observability_metric_labels(labels)
        )
    for normalizer in (
        normalize_group_metric_labels,
        normalize_policy_metric_labels,
        normalize_publication_metric_labels,
    ):
        normalized = normalizer(name, labels)
        if normalized is not None:
            return _normalize_common_metric_labels(normalized)
    return _normalize_common_metric_labels(labels)
