"""Core Prometheus metric label policy and single-label normalizers."""

from __future__ import annotations

from bioetl.domain.observability_contract import normalize_observability_pipeline_label
from bioetl.domain.ports import MetricLabels
from bioetl.infrastructure.observability._prometheus_metric_label_normalizers import (
    normalize_adapter_endpoint_label,
    normalize_adapter_operation_label,
    normalize_filter_source_kind_label,
    normalize_flow_stage,
    normalize_postrun_phase,
    normalize_runtime_phase,
    normalize_runtime_stage,
)
from bioetl.infrastructure.observability.prometheus_metric_label_policy_sets import (
    _ADAPTER_ENDPOINT_LABEL_METRICS,
    _ADAPTER_OPERATION_LABEL_METRICS,
    _FILTER_SOURCE_KIND_LABEL_METRICS,
    _FLOW_STAGE_LABEL_METRICS,
    _PHASE_LABEL_METRICS,
    _POSTRUN_PHASE_LABEL_METRICS,
    _STAGE_LABEL_METRICS,
    _TABLE_LABEL_METRICS,
    APPROVED_ENDPOINT_LABEL_METRICS,
    APPROVED_TABLE_LABEL_METRICS,
    FORBIDDEN_PROMETHEUS_LABEL_NAMES,
    _StringLabelNormalizer,
)

__all__ = [
    "normalize_group_metric_labels",
    "validate_metric_label_policy",
]


def validate_metric_label_policy(name: str, labels: MetricLabels) -> None:
    """Reject high-cardinality or raw labels before Prometheus dispatch."""
    label_names = frozenset(labels)
    forbidden = label_names & FORBIDDEN_PROMETHEUS_LABEL_NAMES
    if forbidden:
        formatted = ", ".join(sorted(forbidden))
        raise ValueError(
            f"Forbidden high-cardinality Prometheus label(s) for {name}: {formatted}"
        )
    if "endpoint" in label_names and name not in APPROVED_ENDPOINT_LABEL_METRICS:
        raise ValueError(
            f"Prometheus label 'endpoint' is only allowed for adapter endpoint "
            f"metrics; got {name}"
        )
    if "source_file" in label_names:
        raise ValueError(
            f"Prometheus label 'source_file' is not allowed for runtime metrics; "
            f"use bounded source_kind labels instead; got {name}"
        )
    if "table" in label_names and name not in APPROVED_TABLE_LABEL_METRICS:
        raise ValueError(
            f"Prometheus label 'table' is only allowed for reviewed "
            f"table-scoped metrics; got {name}"
        )


def _normalize_single_metric_label(
    labels: MetricLabels,
    *,
    key: str,
    default: str,
    normalize: _StringLabelNormalizer,
) -> MetricLabels:
    return {
        **labels,
        key: normalize(str(labels.get(key, default))),
    }


def _normalize_simple_string_label(
    labels: MetricLabels,
    *,
    key: str,
    default: str,
) -> MetricLabels:
    return {
        **labels,
        key: str(labels.get(key, default)),
    }


def _optional_string_label(labels: MetricLabels, key: str) -> str | None:
    value = labels.get(key)
    return value if isinstance(value, str) else None


def normalize_group_metric_labels(
    name: str,
    labels: MetricLabels,
) -> MetricLabels | None:
    """Normalize simple one-label metric families with shared dispatch rules."""
    for metric_names, key, default, normalize in (
        (
            _ADAPTER_ENDPOINT_LABEL_METRICS,
            "endpoint",
            "/unknown",
            normalize_adapter_endpoint_label,
        ),
        (
            _ADAPTER_OPERATION_LABEL_METRICS,
            "operation",
            "other",
            normalize_adapter_operation_label,
        ),
        (
            _FILTER_SOURCE_KIND_LABEL_METRICS,
            "source_kind",
            "other",
            normalize_filter_source_kind_label,
        ),
        (
            _TABLE_LABEL_METRICS,
            "table",
            "unknown",
            normalize_observability_pipeline_label,
        ),
        (_STAGE_LABEL_METRICS, "stage", "other", normalize_runtime_stage),
        (_FLOW_STAGE_LABEL_METRICS, "flow_stage", "other", normalize_flow_stage),
        (_PHASE_LABEL_METRICS, "phase", "other", normalize_runtime_phase),
        (_POSTRUN_PHASE_LABEL_METRICS, "phase", "other", normalize_postrun_phase),
    ):
        if name in metric_names:
            return _normalize_single_metric_label(
                labels,
                key=key,
                default=default,
                normalize=normalize,
            )
    return None
