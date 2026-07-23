"""Metric policy set declarations for Prometheus label governance."""

from __future__ import annotations

from collections.abc import Callable

from bioetl.infrastructure.observability._prometheus_metric_label_normalizers import (
    normalize_composite_phase_error_kind,
    normalize_composite_phase_loss_kind,
    normalize_composite_phase_record_outcome,
    normalize_composite_phase_retry_kind,
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
        "filesystem_path",
        "source_file",
        "file_path",
        "url",
        "raw_url",
        "query",
        "query_string",
        "raw_exception_message",
        "dataset_hash",
        "source_batch_id",
    }
)
_ADAPTER_ENDPOINT_LABEL_METRICS = frozenset(
    {
        "bioetl_adapter_request_duration_seconds",
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
        "bioetl_gold_write_attempts_total",
        "bioetl_gold_write_outcomes_total",
        "bioetl_gold_write_duration_seconds",
        "bioetl_gold_validation_failures_total",
        "bioetl_gold_lifecycle_state_total",
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
_PUBLICATION_VOCAB_DRIFT_LABEL_METRICS = frozenset(
    {"bioetl_publication_raw_vocab_unknown_total"}
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
_PHASE_LABEL_KEY_BY_METRIC_GROUP: tuple[
    tuple[frozenset[str], str, _StringLabelNormalizer],
    ...,
] = (
    (
        _COMPOSITE_PHASE_RECORDS_METRICS,
        "outcome",
        normalize_composite_phase_record_outcome,
    ),
    (
        _COMPOSITE_PHASE_ERRORS_METRICS,
        "error_kind",
        normalize_composite_phase_error_kind,
    ),
    (
        _COMPOSITE_PHASE_LOSS_METRICS,
        "loss_kind",
        normalize_composite_phase_loss_kind,
    ),
    (
        _COMPOSITE_PHASE_RETRIES_METRICS,
        "retry_kind",
        normalize_composite_phase_retry_kind,
    ),
)

__all__ = [
    "APPROVED_ENDPOINT_LABEL_METRICS",
    "APPROVED_SOURCE_FILE_LABEL_METRICS",
    "APPROVED_TABLE_LABEL_METRICS",
    "FORBIDDEN_PROMETHEUS_LABEL_NAMES",
    "OBSERVABILITY_EVENTS_COUNTER_NAME",
]
