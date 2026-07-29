# BioETL Runtime - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-runtime.json`

## Overview

Dashboard `2. Runtime` is an L2 incident surface for runtime triage. It uses shared shell/status/ID/provenance contracts and provides rich runtime triage rows across stage backlog, errors, blockers, and escalation. Shipped dashboard JSON is the source of truth.

Where a Counter appears inside `max_over_time()`, the value is Pushgateway
snapshot evidence, a snapshot denominator, or a presence gate. Event deltas use
`increase()`; exact multi-run totals come from RunLedger.

## Key Panels

### 1. Navigation
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
- **Data sources:** BioETL Ops HTTP control-plane identity endpoint
  `/ops/control-plane/identity-table`; this is not a Prometheus panel.

### 5. Processed Records
- **Type:** Table
- **Purpose:** Show records processed by stage for selected runs.
- **Data sources:** BioETL Ops HTTP
  `/ops/observability/processed-records`; this is not a Prometheus panel.

### 7. Metrics Evidence
- **Type:** Stat
- **Purpose:** Confidence chip for missing/stale scrape or rule-group evidence
  (not pipeline health). Non-zero makes runtime Status `INCOMPLETE`.
- **Data sources:** `bioetl_runtime_trust_gap_status_10m`
- **DSA-05:** Do not present SCRAPING/gap as a peer OK health KPI.

### 8. Monitor Aggregate Stage Lag
- **Type:** Timeseries
- **Purpose:** Continuous stage lag seconds by stage for localization (not discrete state timeline; not exact-run chronology).
- **Data sources:** `bioetl_stage_lag_seconds` (table fallback: Inspect Stage Expectedness)
- **Frame contract:** range Prom query must render a time field; do not use `state-timeline` for continuous lag.

### 9. Runtime Blockers
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

### 38. Secondary KPIs (collapsed; not peer first-screen cards)
- **Type:** Row
- **Purpose:** Group secondary selected-range runtime evidence.
- **Data sources:** Prometheus range evidence from the nested panels.

### 39. Run context (thin) -> Run Explorer hub
- **Type:** Row
- **Purpose:** Group selected-run identity and processed-record HTTP evidence.
- **Data sources:** BioETL Ops HTTP.

### 40. Workflow band (merged from bioetl-workflow-overview)
- **Type:** Row
- **Purpose:** Group workflow-level failure evidence retained on Runtime.
- **Data sources:** Prometheus workflow and pipeline-step counters.

### 41. Failed Workflow Runs / Range
- **Type:** Stat
- **Purpose:** Count failed workflow runs in the selected range.
- **Data sources:** Workflow run failure metrics.

### 42. Failed Pipeline Steps / Range
- **Type:** Stat
- **Purpose:** Count failed pipeline steps in the selected range.
- **Data sources:** Pipeline-step failure metrics.

## Variables

- `workflow`, `pipeline`, `run_type`, and `run_id` are the shared primary dashboard context shell.
- `stage` narrows stage-specific evidence where the panel owns that selector.

## Notes

- This dashboard is an L2 incident surface, not a legacy CPU/RSS/GC dashboard.
- It uses shared shell/status/ID/provenance contracts across all runtime dashboards.
- Row-based workflows (Detect, Localize, Escalate) provide structured triage
  paths and remain collapsed until the headline/cause row points to one branch.
- GLOBAL panels show cross-scope aggregate signals for escalation context.
