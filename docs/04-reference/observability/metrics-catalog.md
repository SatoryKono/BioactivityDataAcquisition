# Metrics Catalog

Complete catalog of all Prometheus metrics defined in BioETL observability system.

**Runtime Metrics: 170** (excluding aliases; derived from
`REGISTERED_PROMETHEUS_METRIC_NAMES`)
**Governed Recording/Current-State Metrics: 41**

Canonical reconciliation command:
`python -m scripts.engineering.qa report-observability-metric-inventory --json`.

## Table of Contents

- [Adapter Metrics](#adapter-metrics) - 17 metrics
- [Core Metrics](#core-metrics) - 45 metrics
- [Health Metrics](#health-metrics) - 13 metrics
- [Pipeline Checkpoint Metrics](#pipeline-checkpoint-metrics) - 7 metrics
- [Pipeline Composite Metrics](#pipeline-composite-metrics) - 1 metric
- [Pipeline Control Plane Metrics](#pipeline-control-plane-metrics) - 16 metrics
- [Pipeline Lifecycle Metrics](#pipeline-lifecycle-metrics) - 8 metrics
- [Pipeline Lineage Metrics](#pipeline-lineage-metrics) - 3 metrics
- [Pipeline Memory Metrics](#pipeline-memory-metrics) - 4 metrics
- [Pipeline Quality Metrics](#pipeline-quality-metrics) - 6 metrics
- [Pipeline Replay Metrics](#pipeline-replay-metrics) - 4 metrics
- [Pipeline Transform Metrics](#pipeline-transform-metrics) - 3 metrics
- [Pipeline Workflow Metrics](#pipeline-workflow-metrics) - 13 metrics
- [Storage Metrics](#storage-metrics) - 30 metrics
- [Governed Recording And Current-State Metrics](#governed-recording-and-current-state-metrics) - 41 metrics

---

## Adapter Metrics

*File: `_metrics_defs_adapter.py`*

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `bioetl_adapter_request_duration_seconds` | Histogram | provider, endpoint | Duration of adapter API requests in seconds |
| `bioetl_adapter_requests_total` | Counter | provider, endpoint, status | Total adapter API requests |
| `bioetl_adapter_batch_size` | Histogram | provider, endpoint | Distribution of adapter response batch sizes |
| `bioetl_adapter_dropped_duplicates_total` | Counter | provider, entity_type | Total duplicate records dropped by adapter dedup |
| `bioetl_adapter_fallback_attempts_total` | Counter | provider, operation | Total fallback resolution candidates processed by adapter flows |
| `bioetl_adapter_fallback_hits_total` | Counter | provider, operation | Total records resolved via fallback paths |
| `bioetl_adapter_fallback_hit_rate` | Gauge | provider, operation | Fallback hit-rate for adapter flows (0-1) |
| `bioetl_adapter_error_taxonomy_total` | Counter | provider, operation, error_category, error_type | Error taxonomy counter for adapter failures |
| `bioetl_data_source_retries_total` | Counter | provider, operation | Total data source retry attempts |
| `bioetl_data_source_retry_exhausted_total` | Counter | provider, operation | Total data source retry exhaustions |
| `bioetl_http_request_duration_seconds` | Histogram | provider, method, status | Duration of HTTP requests in seconds |
| `bioetl_http_retries_total` | Counter | provider, method | Total HTTP request retries |
| `bioetl_http_retry_budget_exhausted_total` | Counter | provider, method | Total HTTP requests that exhausted their retry budget |
| `bioetl_http_request_errors_total` | Counter | provider, method, error_type | Total HTTP request errors |
| `bioetl_provider_health_status` | Gauge | provider | Provider health status (0=unhealthy, 1=degraded, 2=healthy) |
| `bioetl_rate_limiter_tokens_available` | Gauge | provider | Current tokens available in rate limiter |
| `bioetl_rate_limiter_wait_seconds` | Histogram | provider | Rate limiter wait time in seconds |

---

## Core Metrics

*File: `_metrics_defs_core.py`*

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `bioetl_pipeline_duration_seconds` | Histogram | pipeline, stage, status, run_type | Duration of pipeline runs in seconds |
| `bioetl_records_processed_total` | Counter | pipeline, stage, run_type | Total number of records processed by the pipeline |
| `bioetl_record_flow_records_total` | Counter | pipeline, run_type, flow_stage | Total records observed in the bounded pipeline flow projection |
| `bioetl_record_flow_invariants_total` | Counter | pipeline, run_type, invariant, status | Terminal invariant outcomes derived from bounded record-flow projections |
| `bioetl_stage_records_total` | Counter | pipeline, run_type, stage, outcome | Total records observed in the canonical stage-model projection |
| `bioetl_pipeline_stage_expected` | Gauge | pipeline, stage | Whether a pipeline stage is expected (1) or disabled (0) per entity config |
| `bioetl_stage_backlog_records` | Gauge | pipeline, run_type, stage | Current bounded unresolved record backlog projected by canonical stage |
| `bioetl_stage_lag_seconds` | Gauge | pipeline, run_type, stage | Current bounded unresolved stage lag in seconds for canonical stage backlogs |
| `bioetl_batch_lifecycle_events_total` | Counter | pipeline, run_type, event, stage, status | Total bounded batch lifecycle events projected by layer stage and outcome status |
| `bioetl_batch_lifecycle_records_total` | Counter | pipeline, run_type, event, stage, status | Total records associated with bounded batch lifecycle event projections |
| `bioetl_output_artifact_publication_events_total` | Counter | pipeline, stage, status | Total bounded output artifact publication outcomes by stage and status |
| `bioetl_composite_phase_records_total` | Counter | pipeline, phase, outcome | Total bounded record projections across canonical composite phases |
| `bioetl_composite_phase_errors_total` | Counter | pipeline, phase, error_kind | Total bounded error projections across canonical composite phases |
| `bioetl_composite_phase_loss_total` | Counter | pipeline, phase, loss_kind | Total bounded loss projections across canonical composite phases |
| `bioetl_composite_phase_retries_total` | Counter | pipeline, phase, retry_kind | Total bounded retry or resume projections across canonical composite phases |
| `bioetl_errors_total` | Counter | pipeline, stage, error_code | Total number of errors encountered |
| `bioetl_batch_size_records` | Histogram | pipeline, stage | Distribution of batch sizes (number of records) |
| `bioetl_filter_ids_loaded_total` | Counter | pipeline, source_kind | Total unique IDs loaded from input filter source |
| `bioetl_filter_ids_duplicates_total` | Counter | pipeline, source_kind | Total duplicate IDs found in input filter source |
| `bioetl_dq_records_quarantined_total` | Counter | pipeline, error_type, run_type | Total number of records quarantined due to data quality issues |
| `bioetl_dq_dispositions_total` | Counter | pipeline, stage, disposition, terminal_status | Total bounded DQ disposition events correlated with terminal run outcomes |
| `bioetl_quarantine_records_total` | Counter | pipeline, reason | Total number of records written to quarantine |
| `bioetl_quarantine_operator_operations_total` | Counter | operation, status | Total number of quarantine explorer/admin operations by operation and status |
| `bioetl_quarantine_operator_duration_seconds` | Histogram | operation, status | Duration of quarantine explorer/admin operations in seconds |
| `bioetl_silver_filter_rejections_total` | Counter | pipeline, run_type, reason_code, rule_type, field | Total number of Silver filter rejections with bounded analytical labels |
| `bioetl_dq_validation_failures_total` | Counter | pipeline, stage, severity | Total number of DQ validation threshold failures |
| `bioetl_dq_check_failures_total` | Counter | pipeline, stage, check_type, severity | Total failed or warning DQ checks by check type |
| `bioetl_circuit_breaker_state` | Gauge | adapter | Current state of the circuit breaker (0=closed, 1=half-open, 2=open) |
| `bioetl_circuit_breaker_open_total` | Counter | adapter | Total calls rejected while the circuit breaker is open |
| `bioetl_circuit_breaker_trips_total` | Counter | adapter | Total number of times the circuit breaker has tripped (opened) |
| `bioetl_circuit_breaker_success_total` | Counter | adapter | Total successful calls through the circuit breaker |
| `bioetl_circuit_breaker_failure_total` | Counter | adapter | Total failed calls through the circuit breaker |
| `bioetl_vacuum_files_removed_total` | Counter | table, layer | Total files removed by vacuum operations |
| `bioetl_dq_validation_score` | Gauge | pipeline, entity | Data quality validation score (0.0-1.0, where 1.0 = all records valid) |
| `bioetl_dq_validation_record_count` | Gauge | pipeline, entity | Record count associated with the latest entity-level DQ validation score |
| `bioetl_data_freshness_seconds` | Gauge | pipeline, entity | Unix timestamp in seconds for the last successful data ingestion for pipeline/entity; consumers derive lag via time() - metric |
| `bioetl_dq_anomaly_detected_total` | Counter | pipeline, metric, severity, anomaly_type | Total number of data quality anomalies detected |
| `bioetl_dq_check_duration_ms` | Histogram | pipeline | Duration of data quality check in milliseconds |
| `bioetl_dq_monitor_enabled` | Gauge | pipeline, entity | Whether anomaly detection is configured for the pipeline/entity (1 enabled, 0 disabled) |
| `bioetl_dq_baseline_updated_total` | Counter | pipeline, metric | Number of times DQ monitor baseline was updated |
| `bioetl_dq_monitor_disabled_total` | Counter | pipeline, entity | Total DQ evaluations executed without an anomaly monitor configured |
| `bioetl_dq_baseline_samples` | Gauge | pipeline, metric | Current number of samples in DQ baseline |
| `bioetl_metrics_publication_events_total` | Counter | pipeline, run_type, target, status | Total best-effort metrics publication attempts by target and status |
| `bioetl_publication_raw_vocab_unknown_total` | Counter | pipeline, provider, field, handling | Total unknown raw publication vocabulary values preserved for drift observability |
| `bioetl_observability_runtime_status` | Gauge | pipeline, component, mode | Current observability component mode for the active pipeline runtime |

---

## Health Metrics

*File: `_metrics_defs_health.py`*

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `bioetl_pipeline_health_check_passed` | Gauge | pipeline, component | Health check status for pipeline components (1=passed, 0=failed) |
| `bioetl_infrastructure_validated` | Gauge | pipeline | Infrastructure validation status (1=validated, 0=not validated) |
| `bioetl_health_check_duration_seconds` | Histogram | pipeline | Duration of health check operations in seconds |
| `bioetl_health_check_status` | Gauge | component | Health check status per component (0=unknown, 1=healthy, 2=degraded) |
| `bioetl_health_check_mode_status` | Gauge | component, mode | Health check status by mode and component (0=unknown, 1=healthy, 2=degraded) |
| `bioetl_health_check_success_total` | Counter | provider | Total successful health checks |
| `bioetl_health_check_degraded_total` | Counter | provider | Total health checks that returned DEGRADED |
| `bioetl_health_check_failures_total` | Counter | provider | Total health checks that failed or returned UNHEALTHY |
| `bioetl_probe_mode_fallback_total` | Counter | pipeline, component, reason | Total probe-mode fallbacks that downgraded data-source health to degraded |
| `bioetl_health_check_latency_seconds` | Histogram | provider | Health check latency in seconds |
| `bioetl_health_check_mode_latency_seconds` | Histogram | provider, mode | Health check latency in seconds by health-check mode |
| `bioetl_provider_health_observed_timestamp_seconds` | Gauge | provider | Unix timestamp of the latest observed provider-health sample |
| `bioetl_provider_observed_universe` | Gauge | provider | Presence gauge for the currently observed provider-health universe |

---

## Pipeline Checkpoint Metrics

*File: `_metrics_defs_pipeline_checkpoint.py`*

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `bioetl_checkpoint_compatibility_events_total` | Counter | pipeline, disposition | Total checkpoint compatibility outcomes observed during resume validation |
| `bioetl_checkpoint_load_events_total` | Counter | pipeline, status | Total checkpoint load decisions observed during runtime and composite resume paths |
| `bioetl_checkpoint_operator_operations_total` | Counter | operation, status | Total checkpoint admin/operator actions by bounded operation and status |
| `bioetl_checkpoint_operator_duration_seconds` | Histogram | operation, status | Duration of checkpoint admin/operator actions in seconds |
| `bioetl_checkpoint_save_events_total` | Counter | pipeline, operation, status | Total checkpoint save outcomes observed during runtime and composite persistence paths |
| `bioetl_checkpoint_saved_at_seconds` | Gauge | pipeline | Unix timestamp of the latest persisted checkpoint per pipeline |
| `bioetl_checkpoint_save_duration_seconds` | Histogram | pipeline, operation, status | Duration of checkpoint save operations in seconds |

---

## Pipeline Composite Metrics

*File: `_metrics_defs_pipeline_composite.py`*

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `bioetl_composite_source_selection_total` | Counter | pipeline, decision_type, selected_source | Total low-cardinality composite source-selection decisions recorded at persistence time |

---

## Pipeline Control Plane Metrics

*File: `_metrics_defs_pipeline_control_plane.py`*

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `bioetl_control_plane_manifest_writes_total` | Counter | pipeline, run_type, status | Total immutable run-manifest persistence attempts |
| `bioetl_control_plane_manifest_write_duration_seconds` | Histogram | pipeline, run_type, status | Latency of immutable run-manifest persistence in seconds |
| `bioetl_control_plane_ledger_appends_total` | Counter | pipeline, event_type, status | Total append attempts for run-ledger entries |
| `bioetl_control_plane_ledger_append_duration_seconds` | Histogram | pipeline, event_type, status | Latency of run-ledger append operations in seconds |
| `bioetl_control_plane_terminal_events_total` | Counter | pipeline, terminal_status | Total terminal run outcomes mirrored from persisted run-ledger entries |
| `bioetl_manifest_ledger_integrity_ratio` | Gauge | pipeline, run_type, integrity_type | Complementary `consistent`/`inconsistent` ratios over ledger-expected manifests; an empty denominator never publishes a healthy value |
| `bioetl_control_plane_reads_total` | Counter | store, operation, status | Total control-plane read and lookup operations by store, operation, and outcome |
| `bioetl_control_plane_read_duration_seconds` | Histogram | store, operation, status | Latency of control-plane read and lookup operations in seconds |
| `bioetl_control_plane_lifecycle_deleted_total` | Counter | surface, replay_impact | Total control-plane lifecycle artifacts deleted by retention application |
| `bioetl_control_plane_lifecycle_delete_candidates` | Gauge | - | Current number of control-plane lifecycle delete candidates in the latest plan |
| `bioetl_control_plane_lifecycle_apply_total` | Counter | dry_run | Total control-plane lifecycle plan apply attempts by dry-run policy |
| `bioetl_control_plane_checkpoint_present` | Gauge | pipeline | Presence gauge for a persisted control-plane checkpoint |
| `bioetl_control_plane_integrity_pair_present` | Gauge | pipeline | Presence gauge for a consistent manifest/ledger integrity pair |
| `bioetl_control_plane_last_observed_timestamp_seconds` | Gauge | pipeline | Unix timestamp of the latest observed control-plane evidence |
| `bioetl_control_plane_ledger_present` | Gauge | pipeline | Presence gauge for a persisted control-plane run ledger |
| `bioetl_control_plane_manifest_present` | Gauge | pipeline | Presence gauge for a persisted control-plane run manifest |

---

## Pipeline Lifecycle Metrics

*File: `_metrics_defs_pipeline_lifecycle.py`*

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `bioetl_pipeline_runs_total` | Counter | pipeline, run_type, status | Total number of pipeline runs |
| `bioetl_phase_duration_seconds` | Histogram | pipeline, phase, status | Duration of pipeline lifecycle phases in seconds |
| `bioetl_postrun_phase_events_total` | Counter | pipeline, phase, status | Total bounded postrun phase outcomes by pipeline, phase, and status |
| `bioetl_postrun_phase_duration_seconds` | Histogram | pipeline, phase, status | Duration of postrun subphases in seconds |
| `bioetl_observability_events_total` | Counter | event, provider, pipeline, severity, error_type | Unified observability events emitted by pipeline observer |
| `bioetl_shutdown_initiated_total` | Counter | reason | Total shutdown initiations |
| `bioetl_shutdown_completed_total` | Counter | reason | Total shutdown completions |
| `bioetl_storage_optimization_total` | Counter | pipeline, status | Total storage optimization operations |

---

## Pipeline Lineage Metrics

*File: `_metrics_defs_pipeline_lineage.py`*

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `bioetl_traced_runs_total` | Counter | pipeline, run_type | Total pipeline runs that started with real tracing enabled |
| `bioetl_lineage_fragments_emitted_total` | Counter | pipeline, layer, status | Total lineage fragment persistence attempts by pipeline and layer |
| `bioetl_lineage_refs_missing_total` | Counter | pipeline, layer, ref_type | Total writes that detected missing upstream lineage references |

---

## Pipeline Memory Metrics

*File: `_metrics_defs_pipeline_memory.py`*

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `bioetl_memory_pressure_events_total` | Counter | pipeline, stage, reason, monitor_mode, status | Total adaptive-memory decisions that observed active pressure |
| `bioetl_memory_batch_resize_events_total` | Counter | pipeline, stage, reason, monitor_mode, status | Total adaptive-memory decisions that changed batch size |
| `bioetl_memory_monitor_fallback_events_total` | Counter | pipeline, stage, reason, monitor_mode, status | Total adaptive-memory decisions emitted while using fallback monitor modes |
| `bioetl_memory_pressure_state` | Gauge | pipeline, stage, reason, monitor_mode, status | Current bounded adaptive-memory pressure state for the latest decision |

---

## Pipeline Quality Metrics

*File: `_metrics_defs_pipeline_quality.py`*

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `bioetl_structural_policy_events_total` | Counter | provider, entity_type, action | Total structural-policy events emitted by transformer structural enforcement |
| `bioetl_structural_policy_shadow_comparisons_total` | Counter | provider, entity_type, comparison | Total shadow comparisons between structural policy and semantic silver filters |
| `bioetl_dq_soft_threshold_exceeded_total` | Counter | pipeline | Total times DQ soft threshold was exceeded |
| `bioetl_dq_context_build_failures_total` | Counter | pipeline, stage, reason | Total failures while building DQ dataframe context for report generation |
| `bioetl_dq_report_skipped_total` | Counter | pipeline, stage, reason | Total DQ report generation skips by pipeline and medallion stage |
| `bioetl_dq_report_generated_total` | Counter | pipeline, stage | Total successfully generated DQ reports by pipeline and medallion stage |

---

## Pipeline Replay Metrics

*File: `_metrics_defs_pipeline_replay.py`*

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `bioetl_replay_reconstructability_events_total` | Counter | pipeline, replay_capability, strict_requirement, status | Total replay reconstructability observations recorded during manifest assembly |
| `bioetl_replay_drift_events_total` | Counter | pipeline, run_type, replay_capability, drift_type, status | Total bounded replay drift observations recorded during manifest assembly |
| `bioetl_replay_duplicate_overwrite_risk_total` | Counter | pipeline, run_type, risk_type | Accepted replay manifests exposing bounded `duplicate` or `overwrite` write risk; both risk series are initialized with zero per accepted manifest |
| `bioetl_replay_lag_seconds` | Gauge | pipeline, run_type, replay_capability, status | Current bounded replay lag observed during manifest assembly |

---

## Pipeline Transform Metrics

*File: `_metrics_defs_pipeline_transform.py`*

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `bioetl_transform_duration_seconds` | Histogram | provider, entity_type | Duration of data transformation in seconds |
| `bioetl_transform_errors_total` | Counter | provider, entity_type, error_type | Total transformation errors |
| `bioetl_filter_combinations_loaded_total` | Counter | pipeline, source_kind | Total filter combinations loaded from multi-filter source |

---

## Pipeline Workflow Metrics

*File: `_metrics_defs_pipeline_workflow.py`*

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `bioetl_workflow_runs_total` | Counter | workflow, status, pipeline_context, run_type_context, provider_context | Total declarative workflow run outcomes by bounded workflow and status |
| `bioetl_workflow_current_status` | Gauge | workflow, pipeline_context, run_type_context, provider_context | Current terminal workflow status by bounded workflow context: 0=OK, 1=WARN, 2=CRIT |
| `bioetl_workflow_expected` | Gauge | workflow, provider | Planned workflow scopes for dashboard selector universes |
| `bioetl_workflow_pipeline_expected` | Gauge | workflow, pipeline, run_type, provider | Planned workflow pipeline/run_type scopes for dashboard selector universes |
| `bioetl_workflow_reconciliation_rows_scanned_total` | Counter | - | Total workflow reconciliation rows scanned |
| `bioetl_workflow_reconciliation_rows_retained_total` | Counter | - | Total workflow reconciliation rows retained |
| `bioetl_workflow_reconciliation_rows_deleted_total` | Counter | - | Total workflow reconciliation rows deleted |
| `bioetl_workflow_row_reconciliation_left_rows_total` | Counter | layer | Total left-side rows inspected by workflow row reconciliation |
| `bioetl_workflow_row_reconciliation_right_rows_total` | Counter | layer | Total right-side rows inspected by workflow row reconciliation |
| `bioetl_workflow_row_reconciliation_kept_rows_total` | Counter | layer | Total rows retained by workflow row reconciliation |
| `bioetl_workflow_row_reconciliation_excluded_rows_total` | Counter | layer | Total rows excluded by workflow row reconciliation |
| `bioetl_workflow_step_events_total` | Counter | workflow, step_kind, status, pipeline_context, run_type_context, provider_context | Total declarative workflow step outcomes by bounded workflow, step kind, and status |
| `bioetl_workflow_step_duration_seconds` | Histogram | workflow, step_kind, status, pipeline_context, run_type_context, provider_context | Duration of declarative workflow step execution by bounded workflow, step kind, and status |

---

## Storage Metrics

*File: `_metrics_defs_storage.py`*

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `bioetl_audit_write_events_total` | Counter | layer, operation, status | Total audit log write outcomes |
| `bioetl_audit_write_duration_seconds` | Histogram | layer, operation, status | Duration of audit log write operations in seconds |
| `bioetl_audit_query_events_total` | Counter | layer_filter, status | Total audit query outcomes |
| `bioetl_audit_query_duration_seconds` | Histogram | layer_filter, status | Duration of audit query operations in seconds |
| `bioetl_bronze_write_duration_seconds` | Histogram | provider, entity | Duration of bronze write operations in seconds |
| `bioetl_bronze_records_written_total` | Counter | provider, entity | Total records written to bronze layer |
| `bioetl_bronze_write_attempts_total` | Counter | provider, entity | Total Bronze write attempts |
| `bioetl_bronze_bytes_written_total` | Counter | provider, entity | Total bytes written to bronze layer (compressed) |
| `bioetl_bronze_files_removed_total` | Counter | operation | Total Bronze files removed by cleanup maintenance |
| `bioetl_bronze_bytes_freed_total` | Counter | operation | Total Bronze bytes freed by cleanup maintenance |
| `bioetl_bronze_write_total_duration_seconds` | Histogram | provider, entity | Total Bronze write duration, including side effects and metadata writes |
| `bioetl_policy_violations_total` | Counter | layer, mode | Total write policy violations |
| `bioetl_silver_merge_retries_total` | Counter | pipeline, retry_type | Total Silver merge retry attempts emitted by storage resilience helpers |
| `bioetl_silver_merge_failures_total` | Counter | pipeline, final_reason | Total exhausted Silver merge failures emitted by storage resilience helpers |
| `bioetl_silver_validation_failures_total` | Counter | table, pipeline | Total silver schema validation failures |
| `bioetl_gold_write_attempts_total` | Counter | pipeline, table, mode | Total Gold write attempts entering the storage write pipeline |
| `bioetl_gold_write_outcomes_total` | Counter | pipeline, table, mode, status | Total Gold write terminal outcomes emitted by the storage write pipeline |
| `bioetl_gold_write_duration_seconds` | Histogram | pipeline, table, mode, status | Duration of Gold write operations in seconds |
| `bioetl_gold_validation_failures_total` | Counter | pipeline, table, mode, error_type | Total Gold write validation failures before physical storage dispatch |
| `bioetl_gold_lifecycle_state_total` | Counter | pipeline, table, state | Total application-owned Gold lifecycle state decisions |
| `bioetl_metadata_write_retries_total` | Counter | layer, provider, pipeline, reason | Total metadata sidecar atomic-write retry attempts |
| `bioetl_metadata_write_outcomes_total` | Counter | layer, provider, pipeline, status, final_reason | Total metadata sidecar write outcomes |
| `bioetl_silver_csv_export_start_total` | Counter | table, pipeline | Total Silver CSV export operations started |
| `bioetl_silver_csv_export_success_total` | Counter | table, pipeline | Total successful Silver CSV export operations |
| `bioetl_silver_csv_export_failures_total` | Counter | table, pipeline, error_type | Total failed Silver CSV export operations |
| `bioetl_silver_vacuum_start_total` | Counter | - | Total Silver vacuum operations started |
| `bioetl_silver_vacuum_success_total` | Counter | - | Total successful Silver vacuum operations |
| `bioetl_silver_vacuum_files_removed` | Gauge | - | Current number of files removed by the latest Silver vacuum operation |
| `bioetl_silver_optimize_start_total` | Counter | - | Total Silver optimize operations started |
| `bioetl_silver_optimize_success_total` | Counter | - | Total successful Silver optimize operations |

---

## Governed Recording And Current-State Metrics

*Source: `configs/quality/observability_metric_declarations.yaml` and
`grafana/prometheus-rules/*.yml`*

These names are Prometheus recording rules, dashboard current-state projections,
or policy-governed metric contracts. They are not all emitted directly by
`prometheus_client` collectors, but they are part of the shipped observability
surface used by dashboards, alerts, and metric-governance checks.

## Governed Policy Aliases

This table is the independently published, bidirectional documentation contract
for compatibility and query-policy aliases. These names are deliberately kept
separate from actual `record:` outputs and direct runtime collector families.

| Metric Name | Classification |
|-------------|----------------|
| `bioetl_alerts_active_total` | Policy alias |
| `bioetl_alerts_firing_total` | Policy alias |
| `bioetl_control_plane_current_status` | Policy alias |
| `bioetl_control_plane_status` | Policy alias |
| `bioetl_current_status` | Policy alias |
| `bioetl_dq_blocked_records` | Policy alias |
| `bioetl_dq_check_duration_seconds` | Policy alias |
| `bioetl_dq_status` | Policy alias |
| `bioetl_pipeline_phase_duration_seconds` | Policy alias |
| `bioetl_provider_status` | Policy alias |
| `bioetl_runtime_status` | Policy alias |
| `bioetl_silver_filter_reject_field_total` | Policy alias |
| `bioetl_silver_filter_reject_reason_total` | Policy alias |
| `bioetl_silver_reject_rate` | Policy alias |
| `bioetl_workflow_status` | Policy alias |

## Governed Recording And Current-State Inventory

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `bioetl_alerts_active_total` | Recording rule | rule-defined | Active alert count projection for alert/SLO dashboards |
| `bioetl_alerts_firing_total` | Recording rule | rule-defined | Firing alert count projection for alert/SLO dashboards |
| `bioetl_checkpoint_age_seconds` | Recording rule | pipeline | Current checkpoint age derived from checkpoint save timestamp |
| `bioetl_control_plane_status` | Recording rule | rule-defined | Control-plane severity/status projection |
| `bioetl_current_status` | Recording rule | rule-defined | Top-level current system status projection |
| `bioetl_dq_blocked_records` | Recording rule | rule-defined | DQ-blocked record count projection |
| `bioetl_dq_check_duration_seconds` | Recording rule | rule-defined | Seconds-based DQ check duration projection for dashboard formulas |
| `bioetl_dq_status` | Recording rule | rule-defined | DQ status projection for dashboard and alert summaries |
| `bioetl_pipeline_phase_duration_seconds` | Recording rule | rule-defined | Pipeline phase duration projection normalized for dashboard use |
| `bioetl_provider_status` | Recording rule | rule-defined | Provider status projection for provider health dashboards |
| `bioetl_runtime_status` | Recording rule | rule-defined | Runtime status projection for overview/runtime dashboards |
| `bioetl_silver_filter_reject_field_total` | Recording rule | field | Silver reject count grouped by field |
| `bioetl_silver_filter_reject_reason_total` | Recording rule | reason_code | Silver reject count grouped by reason |
| `bioetl_silver_reject_rate` | Recording rule | rule-defined | Silver reject-rate projection for reject explorer and DQ dashboards |
| `bioetl_workflow_status` | Recording rule | workflow | Workflow status projection for dashboard summaries |
| `bioetl_processed_records_bronze_current` | Recording rule | rule-defined | Current Bronze processed-record projection |
| `bioetl_processed_records_gold_deduplicated_current` | Recording rule | rule-defined | Current Gold deduplicated-record projection |
| `bioetl_processed_records_gold_excluded_by_contract_current` | Recording rule | rule-defined | Current Gold records excluded by contract projection |
| `bioetl_processed_records_gold_quarantined_current` | Recording rule | rule-defined | Current Gold quarantined-record projection |
| `bioetl_processed_records_gold_skipped_current` | Recording rule | rule-defined | Current Gold skipped-record projection |
| `bioetl_processed_records_gold_written_current` | Recording rule | rule-defined | Current Gold written-record projection |
| `bioetl_processed_records_reconciliation_status` | Recording rule | rule-defined | Current processed-record reconciliation status projection |
| `bioetl_processed_records_silver_deduplicated_current` | Recording rule | rule-defined | Current Silver deduplicated-record projection |
| `bioetl_processed_records_silver_filtered_out_current` | Recording rule | rule-defined | Current Silver filtered-out-record projection |
| `bioetl_processed_records_silver_quarantined_current` | Recording rule | rule-defined | Current Silver quarantined-record projection |
| `bioetl_processed_records_silver_skipped_current` | Recording rule | rule-defined | Current Silver skipped-record projection |
| `bioetl_processed_records_silver_valid_current` | Recording rule | rule-defined | Current Silver valid-record projection |
| `bioetl_dq_current_reason` | Recording rule | pipeline, reason, severity | Bounded current DQ reasons; `gold_contract_exclusions` is warn-only and must not escalate runtime CRIT |
| `bioetl_dq_current_status` | Recording rule | rule-defined | Current DQ status signal used by L0/L1 dashboards |
| `bioetl_l0_input_status` | Recording rule | rule-defined | L0 input status projection |
| `bioetl_l0_status` | Recording rule | rule-defined | L0 overall status projection |
| `bioetl_l1_control_plane_current_status` | Recording rule | rule-defined | L1 control-plane current status projection |
| `bioetl_l1_dq_status` | Recording rule | rule-defined | L1 DQ status projection |
| `bioetl_l1_gold_lifecycle_status` | Recording rule | rule-defined | L1 Gold lifecycle status projection |
| `bioetl_l1_provider_global_status` | Recording rule | rule-defined | L1 provider global status projection |
| `bioetl_l1_runtime_blocker_status` | Recording rule | rule-defined | L1 runtime blocker status projection |
| `bioetl_l1_workflow_global_status` | Recording rule | rule-defined | L1 workflow global status projection |
| `bioetl_l1_workflow_selected_status` | Recording rule | rule-defined | L1 selected-workflow status projection |
| `bioetl_provider_current_status` | Recording rule | rule-defined | Provider current status projection |
| `bioetl_runtime_current_status` | Recording rule | pipeline, run_type | Runtime current status projection used by overview/workflow dashboards |
| `bioetl_workflow_pipeline_verdict_status` | Recording rule | pipeline, run_type | Workflow-to-pipeline verdict projection for workflow dashboard handoff |

---

## Summary

- **Runtime Metrics**: 170 (excluding aliases; canonical registry-backed count)
- **Governed Recording/Current-State Metrics**: 41
- **Total Categories**: 15
- **Metric Types Distribution**:
  - Counter: 112 metrics
  - Histogram: 25 metrics
  - Gauge: 26 metrics

## Notes

- `_metrics_defs_pipeline.py` is a facade module that re-exports metrics from other pipeline submodules and does not define new metrics
- Circuit breaker state values: 0=closed, 1=half-open, 2=open
- Provider health status values: 0=unhealthy, 1=degraded, 2=healthy
- Workflow status values: 0=OK, 1=WARN, 2=CRIT
