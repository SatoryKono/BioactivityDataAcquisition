"""Metric label normalization dispatch for Prometheus metrics."""

from __future__ import annotations

from bioetl.domain.observability_contract import (
    normalize_observability_metric_labels,
    normalize_observability_pipeline_label,
)
from bioetl.domain.ports import MetricLabels
from bioetl.infrastructure.observability._prometheus_metric_label_normalizers import (
    normalize_adapter_endpoint_label,
    normalize_adapter_operation_label,
    normalize_batch_lifecycle_event,
    normalize_dq_check_type,
    normalize_dq_disposition,
    normalize_dq_severity,
    normalize_dq_stage,
    normalize_filter_source_kind_label,
    normalize_flow_stage,
    normalize_observability_component,
    normalize_observability_mode,
    normalize_postrun_phase,
    normalize_publication_status,
    normalize_publication_target,
    normalize_publication_vocab_field,
    normalize_publication_vocab_handling,
    normalize_publication_vocab_provider,
    normalize_quarantine_reason,
    normalize_record_flow_invariant,
    normalize_record_flow_invariant_status,
    normalize_runtime_phase,
    normalize_runtime_stage,
    normalize_silver_filter_field,
    normalize_silver_filter_reason_code,
    normalize_silver_filter_rule_type,
    normalize_stage_model_outcome,
    normalize_stage_model_stage,
    normalize_structural_action,
    normalize_structural_comparison,
    normalize_terminal_status,
)
from bioetl.infrastructure.observability.prometheus_metric_label_policy_sets import (
    _ADAPTER_ENDPOINT_LABEL_METRICS,
    _ADAPTER_OPERATION_LABEL_METRICS,
    _BATCH_LIFECYCLE_LABEL_METRICS,
    _FILTER_SOURCE_KIND_LABEL_METRICS,
    _FLOW_STAGE_LABEL_METRICS,
    _METRICS_PUBLICATION_LABEL_METRICS,
    _OBSERVABILITY_RUNTIME_STATUS_METRICS,
    _OUTPUT_ARTIFACT_PUBLICATION_LABEL_METRICS,
    _PHASE_LABEL_KEY_BY_METRIC_GROUP,
    _PHASE_LABEL_METRICS,
    _POSTRUN_PHASE_LABEL_METRICS,
    _PUBLICATION_VOCAB_DRIFT_LABEL_METRICS,
    _STAGE_BACKLOG_LABEL_METRICS,
    _STAGE_LABEL_METRICS,
    _STAGE_LAG_LABEL_METRICS,
    _STAGE_MODEL_LABEL_METRICS,
    _TABLE_LABEL_METRICS,
    APPROVED_ENDPOINT_LABEL_METRICS,
    APPROVED_TABLE_LABEL_METRICS,
    FORBIDDEN_PROMETHEUS_LABEL_NAMES,
    OBSERVABILITY_EVENTS_COUNTER_NAME,
    _StringLabelNormalizer,
)

__all__ = ["normalize_metric_dispatch_labels", "validate_metric_label_policy"]


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


def _normalize_group_metric_labels(
    name: str,
    labels: MetricLabels,
) -> MetricLabels | None:
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


def _normalize_quarantine_metric_labels(
    name: str,
    labels: MetricLabels,
) -> MetricLabels | None:
    if name == "bioetl_quarantine_records_total":
        return _normalize_single_metric_label(
            labels,
            key="reason",
            default="other",
            normalize=normalize_quarantine_reason,
        )
    if name == "bioetl_dq_records_quarantined_total":
        return _normalize_simple_string_label(
            labels,
            key="run_type",
            default="unknown",
        )
    return None


def _normalize_dq_metric_labels(
    name: str,
    labels: MetricLabels,
) -> MetricLabels | None:
    if name == "bioetl_dq_dispositions_total":
        return {
            **labels,
            "stage": normalize_dq_stage(str(labels.get("stage", "other"))),
            "disposition": normalize_dq_disposition(
                str(labels.get("disposition", "other"))
            ),
            "terminal_status": normalize_terminal_status(
                str(labels.get("terminal_status", "other"))
            ),
        }
    if name == "bioetl_dq_validation_failures_total":
        return {
            **labels,
            "stage": normalize_dq_stage(str(labels.get("stage", "other"))),
            "severity": normalize_dq_severity(str(labels.get("severity", "other"))),
        }
    if name == "bioetl_record_flow_invariants_total":
        return {
            **labels,
            "invariant": normalize_record_flow_invariant(
                str(labels.get("invariant", "other"))
            ),
            "status": normalize_record_flow_invariant_status(
                str(labels.get("status", "other"))
            ),
        }
    if name == "bioetl_dq_check_failures_total":
        return {
            **labels,
            "stage": normalize_dq_stage(str(labels.get("stage", "other"))),
            "check_type": normalize_dq_check_type(
                str(labels.get("check_type", "other"))
            ),
            "severity": normalize_dq_severity(str(labels.get("severity", "other"))),
        }
    return None


def _normalize_silver_filter_metric_labels(
    name: str,
    labels: MetricLabels,
) -> MetricLabels | None:
    if name != "bioetl_silver_filter_rejections_total":
        return None
    return {
        **labels,
        "reason_code": normalize_silver_filter_reason_code(
            _optional_string_label(labels, "reason_code")
        ),
        "rule_type": normalize_silver_filter_rule_type(
            _optional_string_label(labels, "rule_type")
        ),
        "field": normalize_silver_filter_field(_optional_string_label(labels, "field")),
    }


def _normalize_structural_metric_labels(
    name: str,
    labels: MetricLabels,
) -> MetricLabels | None:
    if name == "bioetl_structural_policy_events_total":
        return {
            **labels,
            "action": normalize_structural_action(labels.get("action", "other")),
        }
    if name == "bioetl_structural_policy_shadow_comparisons_total":
        return {
            **labels,
            "comparison": normalize_structural_comparison(
                labels.get("comparison", "other")
            ),
        }
    return None


def _normalize_publication_metric_labels(
    name: str,
    labels: MetricLabels,
) -> MetricLabels | None:
    for normalizer in (
        _normalize_publication_lifecycle_labels,
        _normalize_publication_registry_labels,
        _normalize_publication_stage_labels,
        _normalize_composite_phase_labels,
    ):
        normalized = normalizer(name, labels)
        if normalized is not None:
            return normalized
    return None


def _normalize_publication_lifecycle_labels(
    name: str,
    labels: MetricLabels,
) -> MetricLabels | None:
    if name in _BATCH_LIFECYCLE_LABEL_METRICS:
        return {
            **labels,
            "event": normalize_batch_lifecycle_event(str(labels.get("event", "other"))),
            "stage": normalize_runtime_stage(str(labels.get("stage", "other"))),
            "status": normalize_publication_status(str(labels.get("status", "other"))),
        }
    if name in _OUTPUT_ARTIFACT_PUBLICATION_LABEL_METRICS:
        return {
            **labels,
            "stage": normalize_runtime_stage(str(labels.get("stage", "other"))),
            "status": normalize_publication_status(str(labels.get("status", "other"))),
        }
    return None


def _normalize_publication_registry_labels(
    name: str,
    labels: MetricLabels,
) -> MetricLabels | None:
    if name in _METRICS_PUBLICATION_LABEL_METRICS:
        return {
            **labels,
            "target": normalize_publication_target(str(labels.get("target", "other"))),
            "status": normalize_publication_status(str(labels.get("status", "other"))),
        }
    if name in _PUBLICATION_VOCAB_DRIFT_LABEL_METRICS:
        return {
            **labels,
            "provider": normalize_publication_vocab_provider(
                str(labels.get("provider", "other"))
            ),
            "field": normalize_publication_vocab_field(
                str(labels.get("field", "other"))
            ),
            "handling": normalize_publication_vocab_handling(
                str(labels.get("handling", "other"))
            ),
        }
    if name in _OBSERVABILITY_RUNTIME_STATUS_METRICS:
        return {
            **labels,
            "component": normalize_observability_component(
                str(labels.get("component", "other"))
            ),
            "mode": normalize_observability_mode(str(labels.get("mode", "other"))),
        }
    return None


def _normalize_publication_stage_labels(
    name: str,
    labels: MetricLabels,
) -> MetricLabels | None:
    if name in _STAGE_BACKLOG_LABEL_METRICS:
        return {
            **labels,
            "stage": normalize_stage_model_stage(str(labels.get("stage", "other"))),
        }
    if name in _STAGE_LAG_LABEL_METRICS:
        return {
            **labels,
            "stage": normalize_runtime_stage(str(labels.get("stage", "other"))),
        }
    if name in _STAGE_MODEL_LABEL_METRICS:
        return {
            **labels,
            "stage": normalize_stage_model_stage(str(labels.get("stage", "other"))),
            "outcome": normalize_stage_model_outcome(
                str(labels.get("outcome", "other"))
            ),
        }
    return None


def _normalize_composite_phase_labels(
    name: str,
    labels: MetricLabels,
) -> MetricLabels | None:
    for metric_group, label_key, label_normalizer in _PHASE_LABEL_KEY_BY_METRIC_GROUP:
        if name in metric_group:
            return {
                **labels,
                "phase": normalize_runtime_phase(str(labels.get("phase", "other"))),
                label_key: label_normalizer(str(labels.get(label_key, "other"))),
            }
    return None


def normalize_metric_dispatch_labels(
    name: str,
    labels: MetricLabels,
) -> MetricLabels:
    """Normalize metric labels for metrics with stricter label contracts."""
    validate_metric_label_policy(name, labels)
    if name == OBSERVABILITY_EVENTS_COUNTER_NAME:
        return normalize_observability_metric_labels(labels)
    for normalizer in (
        _normalize_group_metric_labels,
        _normalize_quarantine_metric_labels,
        _normalize_dq_metric_labels,
        _normalize_silver_filter_metric_labels,
        _normalize_structural_metric_labels,
        _normalize_publication_metric_labels,
    ):
        normalized = normalizer(name, labels)
        if normalized is not None:
            return normalized
    return labels
