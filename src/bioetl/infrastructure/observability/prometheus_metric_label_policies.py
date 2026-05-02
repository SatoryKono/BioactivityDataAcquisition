"""Label policy helpers for PrometheusMetrics."""

from __future__ import annotations

from collections.abc import Callable

from bioetl.domain.observability_contract import (
    normalize_observability_metric_labels,
    normalize_observability_pipeline_label,
)
from bioetl.domain.ports import MetricLabels
from bioetl.infrastructure.observability._prometheus_metric_label_normalizers import (
    normalize_adapter_endpoint_label,
    normalize_adapter_operation_label,
    normalize_batch_lifecycle_event,
    normalize_composite_phase_error_kind,
    normalize_composite_phase_loss_kind,
    normalize_composite_phase_record_outcome,
    normalize_composite_phase_retry_kind,
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

OBSERVABILITY_EVENTS_COUNTER_NAME = "bioetl_observability_events_total"
FORBIDDEN_PROMETHEUS_LABEL_NAMES = frozenset(
    {
        "run_id",
        "manifest_id",
        "lineage_fragment_id",
        "record_id",
        "content_hash",
        "payload_hash",
        "request_id",
        "message",
        "raw_message",
        "path",
        "raw_path",
        "source_file",
        "file_path",
        "url",
        "raw_url",
        "query",
        "query_string",
        "dataset_hash",
        "source_batch_id",
    }
)
_ADAPTER_ENDPOINT_LABEL_METRICS = frozenset(
    {
        "bioetl_adapter_request_duration_seconds",
        "bioetl_adapter_request_p95_seconds",
        "bioetl_adapter_requests_total",
        "bioetl_adapter_batch_size",
    }
)
APPROVED_ENDPOINT_LABEL_METRICS = _ADAPTER_ENDPOINT_LABEL_METRICS
_ADAPTER_OPERATION_LABEL_METRICS = frozenset(
    {
        "bioetl_adapter_error_taxonomy_total",
        "bioetl_adapter_fallback_attempts_total",
        "bioetl_adapter_fallback_hit_rate",
        "bioetl_adapter_fallback_hits_total",
        "bioetl_data_source_retries_total",
        "bioetl_data_source_retry_exhausted_total",
    }
)
_SOURCE_FILE_LABEL_METRICS = frozenset[str]()
APPROVED_SOURCE_FILE_LABEL_METRICS = _SOURCE_FILE_LABEL_METRICS
_TABLE_LABEL_METRICS = frozenset(
    {
        "bioetl_silver_csv_export_start_total",
        "bioetl_silver_csv_export_success_total",
        "bioetl_silver_csv_export_failures_total",
        "bioetl_silver_validation_failures_total",
        "bioetl_vacuum_files_removed_total",
    }
)
APPROVED_TABLE_LABEL_METRICS = _TABLE_LABEL_METRICS
_FILTER_SOURCE_KIND_LABEL_METRICS = frozenset(
    {
        "bioetl_filter_ids_loaded_total",
        "bioetl_filter_ids_duplicates_total",
        "bioetl_filter_combinations_loaded_total",
    }
)
_STAGE_LABEL_METRICS = frozenset(
    {
        "bioetl_batch_size_records",
        "bioetl_dq_context_build_failures_total",
        "bioetl_dq_report_generated_total",
        "bioetl_dq_report_skipped_total",
        "bioetl_errors_total",
        "bioetl_pipeline_duration_seconds",
        "bioetl_records_processed_total",
    }
)
_STAGE_MODEL_LABEL_METRICS = frozenset({"bioetl_stage_records_total"})
_STAGE_BACKLOG_LABEL_METRICS = frozenset({"bioetl_stage_backlog_records"})
_STAGE_LAG_LABEL_METRICS = frozenset({"bioetl_stage_lag_seconds"})
_FLOW_STAGE_LABEL_METRICS = frozenset({"bioetl_record_flow_records_total"})
_BATCH_LIFECYCLE_LABEL_METRICS = frozenset(
    {
        "bioetl_batch_lifecycle_events_total",
        "bioetl_batch_lifecycle_records_total",
    }
)
_DQ_DISPOSITION_LABEL_METRICS = frozenset({"bioetl_dq_dispositions_total"})
_METRICS_PUBLICATION_LABEL_METRICS = frozenset(
    {"bioetl_metrics_publication_events_total"}
)
_OUTPUT_ARTIFACT_PUBLICATION_LABEL_METRICS = frozenset(
    {"bioetl_output_artifact_publication_events_total"}
)
_OBSERVABILITY_RUNTIME_STATUS_METRICS = frozenset(
    {"bioetl_observability_runtime_status"}
)
_PHASE_LABEL_METRICS = frozenset({"bioetl_phase_duration_seconds"})
_COMPOSITE_PHASE_RECORDS_METRICS = frozenset({"bioetl_composite_phase_records_total"})
_COMPOSITE_PHASE_ERRORS_METRICS = frozenset({"bioetl_composite_phase_errors_total"})
_COMPOSITE_PHASE_LOSS_METRICS = frozenset({"bioetl_composite_phase_loss_total"})
_COMPOSITE_PHASE_RETRIES_METRICS = frozenset({"bioetl_composite_phase_retries_total"})
_POSTRUN_PHASE_LABEL_METRICS = frozenset(
    {
        "bioetl_postrun_phase_duration_seconds",
        "bioetl_postrun_phase_events_total",
    }
)

type _StringLabelNormalizer = Callable[[str], str]

__all__ = [
    "APPROVED_ENDPOINT_LABEL_METRICS",
    "APPROVED_SOURCE_FILE_LABEL_METRICS",
    "APPROVED_TABLE_LABEL_METRICS",
    "FORBIDDEN_PROMETHEUS_LABEL_NAMES",
    "OBSERVABILITY_EVENTS_COUNTER_NAME",
    "normalize_adapter_endpoint_label",
    "normalize_adapter_operation_label",
    "normalize_batch_lifecycle_event",
    "normalize_composite_phase_error_kind",
    "normalize_composite_phase_loss_kind",
    "normalize_composite_phase_record_outcome",
    "normalize_composite_phase_retry_kind",
    "normalize_dq_check_type",
    "normalize_dq_disposition",
    "normalize_dq_severity",
    "normalize_dq_stage",
    "normalize_filter_source_kind_label",
    "normalize_flow_stage",
    "normalize_metric_dispatch_labels",
    "normalize_observability_component",
    "normalize_observability_mode",
    "normalize_postrun_phase",
    "normalize_publication_status",
    "normalize_publication_target",
    "normalize_quarantine_reason",
    "normalize_record_flow_invariant",
    "normalize_record_flow_invariant_status",
    "normalize_runtime_phase",
    "normalize_runtime_stage",
    "normalize_silver_filter_field",
    "normalize_silver_filter_reason_code",
    "normalize_silver_filter_rule_type",
    "normalize_stage_model_outcome",
    "normalize_stage_model_stage",
    "normalize_structural_action",
    "normalize_structural_comparison",
    "normalize_terminal_status",
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
    if name in _METRICS_PUBLICATION_LABEL_METRICS:
        return {
            **labels,
            "target": normalize_publication_target(str(labels.get("target", "other"))),
            "status": normalize_publication_status(str(labels.get("status", "other"))),
        }
    if name in _OBSERVABILITY_RUNTIME_STATUS_METRICS:
        return {
            **labels,
            "component": normalize_observability_component(
                str(labels.get("component", "other"))
            ),
            "mode": normalize_observability_mode(str(labels.get("mode", "other"))),
        }
    if name in _STAGE_BACKLOG_LABEL_METRICS:
        return {
            **labels,
            "stage": normalize_stage_model_stage(str(labels.get("stage", "other"))),
        }
    if name in _STAGE_LAG_LABEL_METRICS:
        return {
            **labels,
            "stage": normalize_stage_model_stage(str(labels.get("stage", "other"))),
        }
    if name in _STAGE_MODEL_LABEL_METRICS:
        return {
            **labels,
            "stage": normalize_stage_model_stage(str(labels.get("stage", "other"))),
            "outcome": normalize_stage_model_outcome(
                str(labels.get("outcome", "other"))
            ),
        }
    if name in _COMPOSITE_PHASE_RECORDS_METRICS:
        return {
            **labels,
            "phase": normalize_runtime_phase(str(labels.get("phase", "other"))),
            "outcome": normalize_composite_phase_record_outcome(
                str(labels.get("outcome", "other"))
            ),
        }
    if name in _COMPOSITE_PHASE_ERRORS_METRICS:
        return {
            **labels,
            "phase": normalize_runtime_phase(str(labels.get("phase", "other"))),
            "error_kind": normalize_composite_phase_error_kind(
                str(labels.get("error_kind", "other"))
            ),
        }
    if name in _COMPOSITE_PHASE_LOSS_METRICS:
        return {
            **labels,
            "phase": normalize_runtime_phase(str(labels.get("phase", "other"))),
            "loss_kind": normalize_composite_phase_loss_kind(
                str(labels.get("loss_kind", "other"))
            ),
        }
    if name in _COMPOSITE_PHASE_RETRIES_METRICS:
        return {
            **labels,
            "phase": normalize_runtime_phase(str(labels.get("phase", "other"))),
            "retry_kind": normalize_composite_phase_retry_kind(
                str(labels.get("retry_kind", "other"))
            ),
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
