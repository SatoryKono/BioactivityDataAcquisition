# BioETL Overview v2 - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-overview-v2.json`

## Overview

Dashboard `1. Overview` is the primary entry point for incident triage. It uses shared shell/status/ID/provenance contracts and provides a unified view across runtime, DQ, control plane, provider, and workflow surfaces. Shipped dashboard JSON is the source of truth.

Counter panels that use `max_over_time()` show a Pushgateway final snapshot or
a ratio derived from such snapshots. They do not claim an exact total across
multiple runs; use RunLedger for exact reconciliation.

## Key Panels

### 1. Navigate Dashboards
- **Type:** Text
- **Purpose:** Explain dashboard navigation and escalation flow.
- **Data sources:** Dashboard variables and operator copy.

### 2. Inspect Scope & Evidence
- **Type:** Text
- **Purpose:** Show run ID, manifest ID, and replay provenance anchors.
- **Data sources:** Dashboard variables and operator copy.

### 3. Monitor Fleet Health
- **Type:** Stat
- **Purpose:** Current severity for the selected scope.
- **Data sources:** `bioetl_l0_status` (recording rule with label_replace for workflow pipeline mapping)

### 4. Review First Action
- **Type:** Table (`id=215`)
- **Purpose:** Rank up to four urgency-ordered next actions for the current selectors/fleet and hand off to the recommended board.
- **Data sources:** `topk(4, bioetl_l0_next_action_route{…} or NO_ROUTE vector fallback)` via recording rule `bioetl_l0_next_action_route`.
<<<<<<< HEAD
- **Layout:** first-screen width `w=12` (paired with Review Domain Status `w=12`); `cellHeight: md`.
- **Columns (left→right):** Action (primary CTA, short labels, color-text + row link via `action_dashboard_uid`) → Priority (short badge `RUNTIME`/`CP`/`GOLD`/`DQ`/`PROV`/`WF`/`MON`/`NR`, color-background, not row-wide) → Why → Pipeline.
- **Visual hierarchy:** Action is the sole color-text CTA emphasis; Priority is a secondary urgency badge. Table sorted by Priority desc so top row is first click.
||||||| 565fb33295
- **Columns:** Priority (score, color-text), Action (row link via `action_dashboard_uid`), Why, Pipeline.
=======
- **Columns:** Priority (score, color-text), Action (row link via `action_dashboard_uid`), Why, Pipeline.
- **Presentation:** The routing UID remains available to the Action data-link but
  is hidden from the rendered table; the panel is tall enough to show all four
  bounded routes without an internal vertical scrollbar.
>>>>>>> origin/agent/grafana-3cycle-audit-20260805-r3
- **Priority order:** Runtime > Control Plane > Gold lifecycle > DQ > Provider > Workflow > Monitor.
- **Empty/OK:** `MON` / `NR` (MONITOR / NO_ROUTE scores) with muted gray Action; continue monitoring when Fleet Health is OK.
- **Notes:** `run_id` is URL handoff only (never a Prometheus label). Panel `links` / `dataLinks` remain full domain shortcuts (`Open Runtime`, …); primary CTA is the Action field link (RFA-00 / #7569).

### 5. Review Domain Status
- **Type:** Table
- **Purpose:** Show the first-screen deviation-first matrix across Control Plane,
  Runtime, Provider, Data Quality, Data Validation, and Workflow.
- **Data sources:** `bioetl_l0_input_status_selected` (recording rule with label_replace for workflow pipeline mapping)

### 6. Review Runtime Status
- **Type:** Table
- **Purpose:** Show runtime status and blockers.
- **Data sources:** `bioetl_l1_runtime_blocker_status` (recording rule with label_replace for workflow pipeline mapping)

### 7. Review Data Quality Status
- **Type:** Table
- **Purpose:** Show DQ status and validation results.
- **Data sources:** `bioetl_l1_dq_status` (recording rule with label_replace for workflow pipeline mapping)

### 8. Review Data Validation Status
- **Type:** Table
- **Purpose:** Show data validation outcomes.
- **Data sources:** Aggregated from DQ recording rules

### 9. Review Control Plane Status
- **Type:** Table
- **Purpose:** Show control plane status and replay blockers.
- **Data sources:** `bioetl_l1_control_plane_current_status` (recording rule with label_replace for workflow pipeline mapping)

### 10. Review Global Provider Status
- **Type:** Table
- **Purpose:** Show provider health and status.
- **Data sources:** `bioetl_l1_provider_global_status` (recording rule)

### 11. Review Workflow Status
- **Type:** Table
- **Purpose:** Show workflow execution status.
- **Data sources:** `bioetl_l1_workflow_global_status` (recording rule with label_replace for workflow pipeline mapping)

### 12. Inspect Historical Trends
- **Type:** Row
- **Purpose:** Collapsed row containing repeated subsystem detail and historical
  trends after the compact Inputs matrix.
- **Data sources:** `bioetl_historical_trends`

### 13. Track Runtime Blockers
- **Type:** Timeseries
- **Purpose:** Show runtime blockers trend over time.
- **Data sources:** `bioetl_l1_runtime_blocker_status` (recording rule with label_replace for workflow pipeline mapping)

### 14. Track Data Quality Status
- **Type:** Timeseries
- **Purpose:** Show DQ status trend over time.
- **Data sources:** `bioetl_l1_dq_status` (recording rule with label_replace for workflow pipeline mapping)

### 15. Track Gold Lifecycle
- **Type:** Timeseries
- **Purpose:** Show Gold lifecycle trend over time.
- **Data sources:** `bioetl_l1_gold_lifecycle_status` (recording rule with label_replace for workflow pipeline mapping)

### 16. Inspect Range Evidence
- **Type:** Row
- **Purpose:** Row-based range evidence workflow.
- **Data sources:** `bioetl_range_evidence`

### 17. Review Failed Runs
- **Type:** Table
- **Purpose:** Show historical failure evidence.
- **Data sources:** `bioetl_historical_failures`

### 18. Review Recent Terminal Runs
- **Type:** Table
- **Purpose:** Show recent terminal run evidence.
- **Data sources:** `bioetl_recent_terminal_runs`

### 19. Track Silver Rejects
- **Type:** Stat
- **Purpose:** Show Silver reject count and rate.
- **Data sources:** `bioetl_silver_rejects`, `bioetl_silver_reject_rate`

### 20. Inspect Domain Diagnostics
- **Type:** Row
- **Purpose:** Row-based diagnostics workflow.
- **Data sources:** `bioetl_diagnostics`

### 21. Navigate Diagnostics
- **Type:** Text
- **Purpose:** Explain diagnostics navigation and handoffs.
- **Data sources:** Dashboard variables and operator copy.

### 22. Review Run Identity
- **Type:** Table
- **Purpose:** Show run ID, pipeline, run type, and timestamp.
- **Data sources:** BioETL Ops HTTP control-plane identity endpoint
  `/ops/control-plane/identity-table`; this is not a Prometheus panel.

### 23. Review Processed Records
- **Type:** Table
- **Purpose:** Show Bronze/Silver/Gold counts and denominator-explicit percentages; both numeric columns are right-aligned.
- **Data sources:** BioETL Ops HTTP
  `/ops/observability/processed-records`; this is not a Prometheus panel.

### 24. Inspect Alerts
- **Type:** Row
- **Purpose:** Expanded alert/SLO evidence immediately after the first-level
  matrix. The visible `Status` and `First Action` retain the critical verdict
  and route, while this compact table exposes alert-level impact.
- **Data sources:** `bioetl_alerts`, `bioetl_slo_pressure`

### 25. Review Active Alerts
- **Type:** Table
- **Purpose:** Show alert state for triage. Severity owns severity color; the alert count colors only its own cell and cannot repaint a warning row as critical.
- **Data sources:** `ALERTS{alertstate="firing"}` (standard Prometheus metric)

### 26. Inspect Run Context
- **Type:** Row
- **Purpose:** Group selected-run identity and processed-record HTTP evidence.
- **Data sources:** BioETL Ops HTTP.

## Recording Rules

This dashboard uses Prometheus recording rules to aggregate and transform raw metrics into L0 (level 0) and L1 (level 1) aggregate status metrics. These recording rules enable complex label manipulation and workflow pipeline mapping.

### L0 Recording Rules (Level 0 - Input/Status)
- `bioetl_l0_status` - Aggregate system status with workflow pipeline mapping via label_replace
- `bioetl_l0_next_action_route` - First action route with workflow pipeline mapping via label_replace
- `bioetl_l0_input_status_selected` - Input status by input type (control_plane, runtime, provider, dq, gold) with workflow pipeline mapping via label_replace

### L1 Recording Rules (Level 1 - Aggregate Status)
- `bioetl_l1_runtime_blocker_status` - Runtime blocker status with workflow pipeline mapping via label_replace
- `bioetl_l1_dq_status` - Data quality status with workflow pipeline mapping via label_replace
- `bioetl_l1_gold_lifecycle_status` - Gold lifecycle status with workflow pipeline mapping via label_replace
- `bioetl_l1_control_plane_current_status` - Control plane status with workflow pipeline mapping via label_replace
- `bioetl_l1_provider_global_status` - Provider global status
- `bioetl_l1_workflow_global_status` - Workflow global status with workflow pipeline mapping via label_replace

### Label Replace Pattern
The recording rules use complex `label_replace` expressions to map workflow pipeline names to their base pipeline names:
```promql
label_replace(label_replace(vector(1), "pipeline_raw", "$pipeline", "", ""), "pipeline", "$1", "pipeline_raw", "^(?:workflow_)?(.*)$")
```
This pattern strips the `workflow_` prefix from pipeline names to enable cross-workflow aggregation.

### Raw Metric Starting Points
Raw metric starting points for this dashboard are:
- **System Status:** `bioetl_l0_status{pipeline=~"chembl_assay",run_type=~"incremental"}`
- **First Action route:** `bioetl_l0_next_action_route{pipeline=~"chembl_assay",run_type=~"incremental"}`
- **Input Status:** `bioetl_l0_input_status_selected{pipeline=~"chembl_assay",run_type=~"incremental"}`

Exact blocker reasons live in the Control Plane, Runtime, Data Quality, Provider Health, and Workflow dashboards. Historical evidence stays in the row above.

## Variables

- `workflow`, `pipeline`, `run_type`, and `run_id` are the shared primary dashboard context shell.
- `stage` narrows stage-specific evidence where the panel owns that selector.

## Notes

- This dashboard is the primary L1 entry point for incident triage.
- It uses shared shell/status/ID/provenance contracts across all primary dashboards.
- Row-based workflows (Inspect Historical Trends, Inspect Range Evidence, Inspect Domain Diagnostics, Inspect Alerts) provide structured triage paths.
- The full-width `Inputs` matrix is the deviation-first subsystem summary.
  Repeated Control Plane, Runtime, Data Quality, Provider, Data Validation, and
  Workflow mirrors live in the collapsed `Inspect Domain Diagnostics` row.
- `Inspect Alerts` is the intentional expanded decision-row exception. L1
  Historical Trends, Range Evidence, and Domain Diagnostics are collapsed
  progressive disclosure.
- First Action panel provides operator guidance based on current state.
