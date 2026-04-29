"""Label policy helpers for PrometheusMetrics."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import PurePath

from bioetl.domain.observability_contract import normalize_observability_metric_labels
from bioetl.domain.ports import MetricLabels

OBSERVABILITY_EVENTS_COUNTER_NAME = "bioetl_observability_events_total"
_ADAPTER_ENDPOINT_LABEL_METRICS = frozenset(
    {
        "bioetl_adapter_request_duration_seconds",
        "bioetl_adapter_request_p95_seconds",
        "bioetl_adapter_requests_total",
        "bioetl_adapter_batch_size",
    }
)
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
_SOURCE_FILE_LABEL_METRICS = frozenset(
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
_FLOW_STAGE_LABEL_METRICS = frozenset({"bioetl_record_flow_records_total"})
_DQ_DISPOSITION_LABEL_METRICS = frozenset({"bioetl_dq_dispositions_total"})
_METRICS_PUBLICATION_LABEL_METRICS = frozenset(
    {"bioetl_metrics_publication_events_total"}
)
_OBSERVABILITY_RUNTIME_STATUS_METRICS = frozenset(
    {"bioetl_observability_runtime_status"}
)
_PHASE_LABEL_METRICS = frozenset({"bioetl_phase_duration_seconds"})
_POSTRUN_PHASE_LABEL_METRICS = frozenset(
    {
        "bioetl_postrun_phase_duration_seconds",
        "bioetl_postrun_phase_events_total",
    }
)

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
_ALLOWED_SILVER_FILTER_REASON_CODE_LABELS = frozenset(
    {
        "required_field_missing",
        "exclude_if_present",
        "column_filter_mismatch",
        "range_filter_mismatch",
        "list_length_filter_mismatch",
        "list_contains_filter_mismatch",
        "required_field_type_mismatch",
        "optional_nonnullable_field_type_mismatch",
        "nullable_field_type_coerced_to_null",
        "other",
    }
)
_ALLOWED_SILVER_FILTER_RULE_TYPE_LABELS = frozenset(
    {
        "required_fields",
        "exclude_if_present",
        "column_filters",
        "range_filters",
        "list_length_filters",
        "list_contains_filters",
        "structural_policy",
        "other",
    }
)
_ALLOWED_SILVER_FILTER_FIELD_LABELS = frozenset(
    {
        "_state",
        "accession",
        "activity_id",
        "assay_description",
        "assay_id",
        "assay_param_id",
        "assay_type",
        "assay_type_description",
        "bao_endpoint",
        "bao_format",
        "bao_label",
        "canonical_smiles",
        "cell_id",
        "cell_name",
        "class_level",
        "component_id",
        "confidence_score",
        "data_validity_comment",
        "description",
        "doc_1",
        "doc_2",
        "doi",
        "inorganic_flag",
        "journal",
        "mapping_status",
        "molecule_id",
        "molecule_type",
        "openalex_id",
        "organism",
        "organism_scientific",
        "other",
        "paper_id",
        "pchembl_value",
        "pmid",
        "potential_duplicate",
        "pref_name",
        "protein_class_id",
        "publication_id",
        "publication_type",
        "publication_year",
        "record_id",
        "relation",
        "relationship_type",
        "sim_id",
        "src_id",
        "standard_flag",
        "standard_relation",
        "standard_type",
        "standard_units",
        "standard_value",
        "structure_type",
        "subcellular_fraction",
        "target_id",
        "target_organism",
        "target_taxonomy_id",
        "target_type",
        "term",
        "term_type",
        "tissue_id",
        "title",
        "type",
        "units",
        "uo_units",
        "value",
    }
)
_ALLOWED_STAGE_LABELS = frozenset(
    {
        "validation",
        "threshold",
        "transform",
        "bronze",
        "silver",
        "gold",
        "postrun",
        "other",
    }
)
_ALLOWED_RUNTIME_STAGE_LABELS = frozenset(
    {
        "pipeline",
        "startup",
        "preflight",
        "lifecycle_clear",
        "execution",
        "postrun",
        "cleanup",
        "bronze",
        "silver",
        "gold",
        "filtered_out",
        "quarantined",
        "transform",
        "validation",
        "write",
        "checkpoint",
        "extract",
        "load",
        "other",
    }
)
_ALLOWED_FLOW_STAGE_LABELS = frozenset(
    {
        "fetched",
        "bronze",
        "silver",
        "gold",
        "filtered_out",
        "quarantined",
        "other",
    }
)
_ALLOWED_STAGE_MODEL_STAGE_LABELS = frozenset(
    {"input", "ingestion", "transform", "validation", "storage", "output", "other"}
)
_ALLOWED_STAGE_MODEL_OUTCOME_LABELS = frozenset(
    {
        "fetched",
        "bronze_written",
        "silver_ready",
        "gold_ready",
        "filtered_out",
        "evaluated",
        "quarantined",
        "silver_written",
        "gold_written",
        "ready",
        "other",
    }
)
_ALLOWED_PHASE_LABELS = frozenset(
    {
        "startup",
        "preflight",
        "lifecycle_clear",
        "execution",
        "postrun",
        "cleanup",
        "preflight_validation",
        "seed",
        "dependencies",
        "enrichment",
        "merge",
        "cross_validation",
        "gold_write",
        "other",
    }
)
_ALLOWED_POSTRUN_PHASE_LABELS = frozenset(
    {
        "dq_evaluation",
        "dq_reports",
        "compaction",
        "vacuum",
        "final_metadata",
        "other",
    }
)
_ALLOWED_SEVERITY_LABELS = frozenset(
    {"soft_fail", "hard_fail", "warning", "error", "other"}
)
_ALLOWED_DQ_DISPOSITION_LABELS = frozenset(
    {"pass", "warn", "quarantine", "skip", "fail", "other"}
)
_ALLOWED_TERMINAL_STATUS_LABELS = frozenset({"success", "failed", "shutdown", "other"})
_ALLOWED_PUBLICATION_TARGET_LABELS = frozenset(
    {"pushgateway", "metrics_server", "other"}
)
_ALLOWED_PUBLICATION_STATUS_LABELS = frozenset(
    {"success", "failed", "skipped", "disabled", "other"}
)
_ALLOWED_OBSERVABILITY_COMPONENT_LABELS = frozenset(
    {"metrics", "tracing", "audit", "dq_monitor", "other"}
)
_ALLOWED_OBSERVABILITY_MODE_LABELS = frozenset({"active", "noop", "disabled", "other"})
_ALLOWED_DQ_CHECK_TYPE_LABELS = frozenset(
    {
        "anomaly_detection",
        "business_rules",
        "completeness",
        "content_hash_integrity",
        "data_freshness",
        "deduplication_stats",
        "encoding_validation",
        "file_integrity",
        "key_nullability",
        "null_rate",
        "raw_field_presence",
        "record_count",
        "referential_integrity",
        "schema_drift",
        "schema_snapshot",
        "scd_integrity",
        "statistical_profile",
        "type_conformance",
        "uniqueness",
        "value_distribution",
        "other",
    }
)
_ALLOWED_STRUCTURAL_ACTION_LABELS = frozenset(
    {
        "presence_quarantine",
        "required_type_quarantine",
        "nullable_type_to_null",
        "optional_nonnullable_quarantine",
        "other",
    }
)
_ALLOWED_STRUCTURAL_COMPARISON_LABELS = frozenset(
    {
        "structural_pass_semantic_pass",
        "structural_pass_semantic_reject",
        "structural_reject_semantic_pass",
        "structural_reject_semantic_reject",
        "other",
    }
)
_ALLOWED_ADAPTER_OPERATION_LABELS = frozenset(
    {
        "doi_resolution",
        "fallback_flow",
        "fetch",
        "fetch_batch",
        "fetch_filtered_with_fallback",
        "health_check",
        "search",
        "title_fallback",
        "other",
    }
)

_DYNAMIC_ENDPOINT_SEGMENT_PATTERNS = (
    re.compile(r"^\d+$"),
    re.compile(
        r"^[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}$",
        re.IGNORECASE,
    ),
    re.compile(r"^[\da-f]{16,}$", re.IGNORECASE),
)


type _StringLabelNormalizer = Callable[[str], str]


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
            _SOURCE_FILE_LABEL_METRICS,
            "source_file",
            "unknown",
            normalize_source_file_label,
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
    if name in _STAGE_MODEL_LABEL_METRICS:
        return {
            **labels,
            "stage": normalize_stage_model_stage(str(labels.get("stage", "other"))),
            "outcome": normalize_stage_model_outcome(
                str(labels.get("outcome", "other"))
            ),
        }
    return None


def normalize_metric_dispatch_labels(
    name: str,
    labels: MetricLabels,
) -> MetricLabels:
    """Normalize metric labels for metrics with stricter label contracts."""
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


def normalize_adapter_endpoint_label(endpoint: str) -> str:
    """Normalize adapter endpoint labels to bounded route-template form."""
    stripped = endpoint.strip()
    if not stripped:
        return "/unknown"
    path = stripped.split("?", 1)[0]
    normalized_segments: list[str] = []
    for segment in path.split("/"):
        if not segment:
            continue
        normalized_segments.append(_normalize_endpoint_segment(segment))
    if not normalized_segments:
        return "/"
    return "/" + "/".join(normalized_segments)


def normalize_source_file_label(source_file: str) -> str:
    """Normalize filter source file labels to basename-only bounded values."""
    stripped = source_file.strip()
    if not stripped:
        return "unknown"
    path_like = stripped.replace("\\", "/")
    basename = PurePath(path_like).name
    candidate = basename or path_like
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "_", candidate.lower())
    collapsed = re.sub(r"_+", "_", normalized).strip("._-")
    if not collapsed:
        return "unknown"
    return collapsed[:64]


def normalize_adapter_operation_label(operation: str) -> str:
    """Normalize adapter operation labels to the reviewed bounded vocabulary."""
    return _normalize_bounded_label(operation, _ALLOWED_ADAPTER_OPERATION_LABELS)


def normalize_quarantine_reason(reason: str) -> str:
    """Normalize quarantine reason to a bounded label set."""
    return _normalize_bounded_label(reason, _ALLOWED_REASON_LABELS)


def normalize_silver_filter_reason_code(reason_code: str | None) -> str:
    """Normalize Silver filter reason_code to a bounded label set."""
    return _normalize_bounded_label(
        reason_code or "other", _ALLOWED_SILVER_FILTER_REASON_CODE_LABELS
    )


def normalize_silver_filter_rule_type(rule_type: str | None) -> str:
    """Normalize Silver filter rule_type to a bounded label set."""
    return _normalize_bounded_label(
        rule_type or "other", _ALLOWED_SILVER_FILTER_RULE_TYPE_LABELS
    )


def normalize_silver_filter_field(field: str | None) -> str:
    """Normalize Silver filter field name to a bounded label set."""
    return _normalize_bounded_label(
        field or "other", _ALLOWED_SILVER_FILTER_FIELD_LABELS
    )


def normalize_dq_stage(stage: str) -> str:
    """Normalize DQ stage label to a bounded label set."""
    return _normalize_bounded_label(stage, _ALLOWED_STAGE_LABELS)


def normalize_runtime_stage(stage: str) -> str:
    """Normalize generic runtime stage labels to a bounded label set."""
    return _normalize_bounded_label(stage, _ALLOWED_RUNTIME_STAGE_LABELS)


def normalize_flow_stage(flow_stage: str) -> str:
    """Normalize record-flow stage labels to the canonical bounded set."""
    return _normalize_bounded_label(flow_stage, _ALLOWED_FLOW_STAGE_LABELS)


def normalize_stage_model_stage(stage: str) -> str:
    """Normalize canonical stage-model stage labels."""
    return _normalize_bounded_label(stage, _ALLOWED_STAGE_MODEL_STAGE_LABELS)


def normalize_stage_model_outcome(outcome: str) -> str:
    """Normalize canonical stage-model outcome labels."""
    return _normalize_bounded_label(outcome, _ALLOWED_STAGE_MODEL_OUTCOME_LABELS)


def normalize_runtime_phase(phase: str) -> str:
    """Normalize lifecycle and composite phase labels to a bounded label set."""
    return _normalize_bounded_label(phase, _ALLOWED_PHASE_LABELS)


def normalize_postrun_phase(phase: str) -> str:
    """Normalize postrun subphase labels to the canonical bounded set."""
    return _normalize_bounded_label(phase, _ALLOWED_POSTRUN_PHASE_LABELS)


def normalize_dq_severity(severity: str) -> str:
    """Normalize DQ severity label to a bounded label set."""
    return _normalize_bounded_label(severity, _ALLOWED_SEVERITY_LABELS)


def normalize_dq_disposition(disposition: str) -> str:
    """Normalize DQ disposition labels to the canonical bounded set."""
    return _normalize_bounded_label(disposition, _ALLOWED_DQ_DISPOSITION_LABELS)


def normalize_terminal_status(terminal_status: str) -> str:
    """Normalize terminal run status labels to the bounded set."""
    return _normalize_bounded_label(terminal_status, _ALLOWED_TERMINAL_STATUS_LABELS)


def normalize_publication_target(target: str) -> str:
    """Normalize metrics publication target labels."""
    return _normalize_bounded_label(target, _ALLOWED_PUBLICATION_TARGET_LABELS)


def normalize_publication_status(status: str) -> str:
    """Normalize metrics publication status labels."""
    return _normalize_bounded_label(status, _ALLOWED_PUBLICATION_STATUS_LABELS)


def normalize_observability_component(component: str) -> str:
    """Normalize observability component labels."""
    return _normalize_bounded_label(component, _ALLOWED_OBSERVABILITY_COMPONENT_LABELS)


def normalize_observability_mode(mode: str) -> str:
    """Normalize observability runtime mode labels."""
    return _normalize_bounded_label(mode, _ALLOWED_OBSERVABILITY_MODE_LABELS)


def normalize_dq_check_type(check_type: str) -> str:
    """Normalize DQ check type label to the configured bounded set."""
    return _normalize_bounded_label(check_type, _ALLOWED_DQ_CHECK_TYPE_LABELS)


def normalize_structural_action(action: str) -> str:
    """Normalize structural action label to a bounded label set."""
    return _normalize_bounded_label(action, _ALLOWED_STRUCTURAL_ACTION_LABELS)


def normalize_structural_comparison(comparison: str) -> str:
    """Normalize structural comparison label to a bounded label set."""
    return _normalize_bounded_label(
        comparison,
        _ALLOWED_STRUCTURAL_COMPARISON_LABELS,
    )


def _normalize_endpoint_segment(segment: str) -> str:
    """Collapse likely dynamic path segments into a stable placeholder."""
    if "{" in segment and "}" in segment:
        return segment
    lowered = segment.lower()
    if lowered.startswith("10."):
        return "{id}"
    if any(pattern.match(lowered) for pattern in _DYNAMIC_ENDPOINT_SEGMENT_PATTERNS):
        return "{id}"
    return segment


def _normalize_bounded_label(value: str, allowed_values: frozenset[str]) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    return normalized if normalized in allowed_values else "other"
