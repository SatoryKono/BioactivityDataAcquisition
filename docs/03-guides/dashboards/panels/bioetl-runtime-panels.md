# BioETL Runtime - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-runtime.json`

## Overview

Dashboard `2. Runtime` is an L2 incident surface for runtime triage. It uses shared shell/status/ID/provenance contracts and provides rich runtime triage rows across stage backlog, errors, blockers, and escalation. Shipped dashboard JSON is the source of truth.

Where a Counter appears inside `max_over_time()`, the value is Pushgateway
snapshot evidence, a snapshot denominator, or a presence gate. Event deltas use
`increase()`; exact multi-run totals come from RunLedger.

## Key Panels

### 1. Review Dashboard Navigation
- **Type:** Text
- **Purpose:** Explain the dashboard navigation and escalation flow.
- **Data sources:** Dashboard variables and operator copy.

### 2. Provenance
- **Type:** Text
- **Purpose:** Show run ID, manifest ID, and replay provenance anchors.
- **Data sources:** Dashboard variables and operator copy.

### 3. Status
- **Type:** Stat
- **Purpose:** Evidence-aware runtime severity: `0=OK`, `1=WARN`, `2=CRIT`,
  `3=INCOMPLETE`, `null=UNKNOWN`. A scrape/rule trust gap forces
  `INCOMPLETE` before zero counters may be trusted.
- **Data sources:** `bioetl_runtime_current_status_trusted`

### 4. ID
- **Type:** Table
- **Purpose:** Show run ID, pipeline, run type, and timestamp for selected scope.
- **Data sources:** Quarantine Explorer HTTP control-plane identity endpoint
  `/ops/control-plane/identity-table`; this is not a Prometheus panel.

### 5. Processed Records
- **Type:** Table
- **Purpose:** Show records processed by stage for selected runs.
- **Data sources:** Quarantine Explorer HTTP
  `/ops/observability/processed-records`; this is not a Prometheus panel.

### 6. Runtime Status
- **Type:** Stat
- **Purpose:** Expanded mirror of the same trust-gated headline rule; it is not
  an independent second verdict.
- **Data sources:** `bioetl_runtime_current_status_trusted`

### 7. Runtime Telemetry Gap
- **Type:** Stat
- **Purpose:** Detect missing/stale scrape or rule-group evidence. Non-zero makes
  both runtime status panels `INCOMPLETE`.
- **Data sources:** `bioetl_runtime_trust_gap_status_10m`

### 8. Runtime Blockers
- **Type:** Table
- **Purpose:** Show active runtime blockers with details.
- **Data sources:** `bioetl_runtime_current_blocker_reason_scoped`

### 9. Monitor Runtime Blockers
- **Type:** Stat
- **Purpose:** Count active runtime blockers as neutral evidence when the count is `0`; non-zero values remain escalation signals.
- **Data sources:** `bioetl_runtime_current_blocker_reason`

### 10. Failed Runs
- **Type:** Stat
- **Purpose:** Count failed runs in selected range; rendered as neutral range evidence so `0` does not compete with the telemetry trust gate.
- **Data sources:** `bioetl_pipeline_runs_total`

### 11. Runtime Error Rate
- **Type:** Stat
- **Purpose:** Show selected-range error rate across stages; zero/low values are neutral range evidence unless current status and telemetry trust are valid.
- **Data sources:** `bioetl_errors_total`

### 12. Worst Stage Lag
- **Type:** Stat
- **Purpose:** Identify the selected-range stage with worst lag; `0s` is neutral range evidence, not an override of telemetry trust.
- **Data sources:** `bioetl_stage_lag_seconds`

### 13. First Action
- **Type:** Text
- **Purpose:** Guide operator to next triage action.
- **Data sources:** Dashboard variables and operator copy.

### 14. Detect
- **Type:** Row
- **Purpose:** Collapsed-by-default detection workflow for stage backlog and
  blocker detail.
- **Data sources:** `bioetl_stage_backlog_records`

### 15. Track Stage Backlog Trend
- **Type:** Timeseries
- **Purpose:** Show stage backlog over time.
- **Data sources:** `bioetl_stage_backlog_records`

### 16. Inspect Stage Expectedness
- **Type:** Table
- **Purpose:** Show stage expectedness and anomaly detection.
- **Data sources:** `bioetl_pipeline_stage_expected`

### 17. Track Records by Stage / Interval
- **Type:** Timeseries
- **Purpose:** Show record flow by stage over time.
- **Data sources:** `bioetl_records_processed_total`

### 18. Inspect Active Runtime Blocker Detail
- **Type:** Table
- **Purpose:** Show detailed blocker information.
- **Data sources:** `bioetl_runtime_current_blocker_reason`

### 19. Localize
- **Type:** Row
- **Purpose:** Collapsed-by-default localization workflow for errors.
- **Data sources:** `bioetl_errors_total`

### 20. Track Pipeline Phase Duration p50/p95/p99
- **Type:** Timeseries
- **Purpose:** Show pipeline phase duration percentiles.
- **Data sources:** `bioetl_pipeline_phase_duration_seconds`

### 21. Track Pipeline Duration p50/p95/p99
- **Type:** Timeseries
- **Purpose:** Show total pipeline duration percentiles.
- **Data sources:** `bioetl_pipeline_duration_seconds`

### 22. Inspect Errors by Stage / Error Code / Range
- **Type:** Table
- **Purpose:** Show error breakdown by stage and error code.
- **Data sources:** `bioetl_errors_total`

### 23. Track Records by Stage / Run Type / Range
- **Type:** Bargauge
- **Purpose:** Show record distribution by stage and run type.
- **Data sources:** `bioetl_records_processed_total`

### 24. Escalate
- **Type:** Row
- **Purpose:** Collapsed-by-default escalation workflow for cross-domain issues.
- **Data sources:** `bioetl_runtime_alert_condition_*`

### 25. Review Runtime-owned escalation
- **Type:** Text
- **Purpose:** Explain escalation ownership and handoffs.
- **Data sources:** Dashboard variables and operator copy.

### 26. Monitor Pipeline Alert Conditions
- **Type:** Stat
- **Purpose:** Show pipeline alert condition status.
- **Data sources:** `bioetl_runtime_alert_condition_pipeline_precondition`

### 27. Monitor No-Records Runs
- **Type:** Stat
- **Purpose:** Count runs with zero records processed.
- **Data sources:** `bioetl_records_processed_total`

### 28. Monitor Memory Pressure Active
- **Type:** Stat
- **Purpose:** Show active memory pressure conditions.
- **Data sources:** `bioetl_memory_pressure_state`

### 29. Review Cross-domain handoffs
- **Type:** Text
- **Purpose:** Explain cross-domain handoff patterns.
- **Data sources:** Dashboard variables and operator copy.

### 30. Inspect DQ Alert Conditions
- **Type:** Stat
- **Purpose:** Show DQ alert conditions.
- **Data sources:** `bioetl_runtime_alert_condition_dq_soft_threshold`

### 31. Inspect Control-plane Alert Conditions
- **Type:** Stat
- **Purpose:** Show control-plane alert conditions.
- **Data sources:** `bioetl_runtime_alert_condition_manifest_write_conflict`

### 32. Inspect Provider Alert Conditions
- **Type:** Stat
- **Purpose:** Show provider alert conditions.
- **Data sources:** `bioetl_runtime_alert_condition_provider_failure`

### 33. Inspect GLOBAL Provider Alert Conditions
- **Type:** Stat
- **Purpose:** Show global provider alert conditions.
- **Data sources:** `bioetl_runtime_alert_condition_provider_adapter_failure`

### 34. Inspect Freshness Lagged Entities >24h
- **Type:** Stat
- **Purpose:** Count entities with freshness lag >24h.
- **Data sources:** `bioetl_data_freshness_seconds`

### 35. Review Process-level signals (GLOBAL)
- **Type:** Text
- **Purpose:** Explain global process-level signals.
- **Data sources:** Dashboard variables and operator copy.

### 36. Track GLOBAL Shutdown Initiated by Reason / Interval
- **Type:** Timeseries
- **Purpose:** Show shutdown initiations by reason.
- **Data sources:** `bioetl_shutdown_initiated_total`

### 37. Track GLOBAL Shutdown Completed by Reason / Interval
- **Type:** Timeseries
- **Purpose:** Show shutdown completions by reason.
- **Data sources:** `bioetl_shutdown_completed_total`

### 38. Tracing-only Log Hygiene (requires optional tracing profile)
- **Type:** Row
- **Purpose:** Collapsed optional log-hygiene evidence; never required for the
  Prometheus-first headline.
- **Data sources:** `{job="bioetl"} | json`

### 39. Inspect Warning Logs
- **Type:** Table
- **Purpose:** Show warning log entries.
- **Data sources:** `{job="bioetl"} | json`

### 40. Inspect GLOBAL Unstructured Logs
- **Type:** Table
- **Purpose:** Show unstructured log entries.
- **Data sources:** `{job="bioetl"} | json`

### 41. Inspect Top Warning Events by Event / Logger / Range
- **Type:** Table
- **Purpose:** Show top warning events by event type and logger.
- **Data sources:** `{job="bioetl"} | json`

### 42. Track GLOBAL Log Hygiene Trend
- **Type:** Timeseries
- **Purpose:** Show log hygiene trend over time.
- **Data sources:** `{job="bioetl"} | json`

## Variables

- `workflow`, `pipeline`, `run_type`, and `run_id` are the shared primary dashboard context shell.
- `stage` narrows stage-specific evidence where the panel owns that selector.

## Notes

- This dashboard is an L2 incident surface, not a legacy CPU/RSS/GC dashboard.
- It uses shared shell/status/ID/provenance contracts across all runtime dashboards.
- Row-based workflows (Detect, Localize, Escalate) provide structured triage
  paths and remain collapsed until the headline/cause row points to one branch.
- GLOBAL panels show cross-scope aggregate signals for escalation context.
