# BioETL Overview v2 - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-overview-v2.json`

## Overview

Dashboard `2. Overview` is the primary entry point for incident triage. It uses shared shell/status/ID/provenance contracts and provides a unified view across runtime, DQ, control plane, provider, and workflow surfaces. Shipped dashboard JSON is the source of truth.

Counter panels that use `max_over_time()` show a Pushgateway final snapshot or
a ratio derived from such snapshots. They do not claim an exact total across
multiple runs; use RunLedger for exact reconciliation.

## Key Panels

Review Run Identity shows four saved fields without pagination: full Run ID,
Pipeline, Run Type, and Started at with the saved UTC offset. Additional manifest,
schema and source identifiers remain in Inspect Additional Run Identity.

The scope banner shows `Pipeline | Run ID`, followed by a line break. Run Type
remains available in the selector. For `cached_bronze_no_remote_probe`, Review
Run Domains displays "Cached Bronze used; provider API was not called."
The saved Provider verdict remains N/A because no remote check was performed;
the table displays an em dash, as for Workflow, and wraps the reason text.

### Overall verdict

The stat panel beside the selected-run scope banner repeats `run_verdict` from
the same source frame as Review Selected Run Status. It retains the selected
Run ID and does not independently infer success or authorize replay. Missing
values display UNKNOWN. The panel occupies x=17/y=2/w=7/h=3; the scope banner
uses the remaining 17 columns.

### 2. Inspect Scope & Evidence
- **Type:** Text
- **Purpose:** Show run ID, manifest ID, and replay provenance anchors.
- **Data sources:** Dashboard variables and operator copy.

### 3. Monitor Scope Health
- **Type:** Stat
- **Purpose:** Current severity for the selected scope.
- **Data sources:** `bioetl_l0_status` (recording rule with label_replace for workflow pipeline mapping)

### 4. Review First Action — removed from shipped JSON

Панель `id=215` (и полные виды `20215`/`30215`) намеренно снята с Overview
(RF-006 #11257, live-подтверждено; issue #11809) — не возвращать ради
соответствия докам. Описание ниже сохранено как историческое.

- **Было:** Table (`id=215`); до двух urgency-ordered next actions;
  источники `bioetl_l0_next_action_route` / `bioetl_l0_next_action_no_route`;
  layout First Action `w=16`, Domain Status `w=8`.
- **Сейчас:** next-action handoff дают Status / Domains / nav с сохранением
  фильтров `${pipeline}/${run_type}/${run_id}` и time range.

### 5. Review Run Domains
- **Type:** Table (`id=9002`)
- **Purpose:** Six fixed domains from the exact persisted run assessment, independent of age and range.
- **Data source:** Selected-run API. Summary panel 9603 reuses this response through the Dashboard datasource.
- **Layout:** Six rows; Domain and Status. Reasons, evidence and actions remain in Inspect Saved Run Evidence.
- **States:** Missing selection is SELECT RUN; missing checks are INCOMPLETE. Missing response is UNKNOWN with the native query error indicator.

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

### 12. Domain Status Tracks
- **Type:** Row
- **Purpose:** Collapsed row containing the full domain matrix plus repeated
  subsystem detail and historical trends after the compact Inputs summary.
- **Data sources:** `bioetl_l0_input_status_selected` and historical L1 tracks

### 12a. Review All Domain Status
- **Type:** Table (`id=9031`)
- **Purpose:** Preserve the complete six-domain current-status matrix below the
  fold after the first-screen four-row cap.
- **Data sources:** `max by (input) (bioetl_l0_input_status_selected{…})`

### 13. Track Runtime Blockers
- **Type:** State timeline
- **Purpose:** Show runtime blockers trend over time.
- **Data sources:** `bioetl_l1_runtime_blocker_status` (recording rule with label_replace for workflow pipeline mapping)

- **Presentation:** Full-width outlined intervals with explicit semantic
  states, visible legend and a 240 px scope axis; absent data remains UNKNOWN.

### 14. Track Data Quality Status
- **Type:** State timeline
- **Purpose:** Show DQ status trend over time.
- **Data sources:** `bioetl_l1_dq_status` (recording rule with label_replace for workflow pipeline mapping)

- **Presentation:** Full-width outlined intervals with explicit semantic
  states, visible legend and a 240 px scope axis; absent data remains UNKNOWN.

### 15. Track Gold Lifecycle
- **Type:** State timeline
- **Purpose:** Show Gold lifecycle trend over time.
- **Data sources:** `bioetl_l1_gold_lifecycle_status` (recording rule with label_replace for workflow pipeline mapping)

- **Presentation:** Full-width outlined intervals with explicit semantic
  states, visible legend and a 240 px scope axis; absent data remains UNKNOWN.

### 16. Inspect Range Evidence
- **Type:** Row
- **Purpose:** Collapsed row-based range evidence workflow.
- **Data sources:** `bioetl_range_evidence`

### 17. Review Failed Runs
- **Type:** Table
- **Purpose:** Show historical failure evidence.
- **Data sources:** `bioetl_historical_failures`

### 18. Review Recent Non-success Terminal Runs
- **Type:** Table
- **Purpose:** Show recent non-success terminal-run evidence in the selected range.
- **Data sources:** `bioetl_pipeline_runs_total` with `status!="success"`

### 19. Track Silver Rejects
- **Type:** Stat
- **Purpose:** Show Silver reject count and rate.
- **Data sources:** `bioetl_silver_rejects`, `bioetl_silver_reject_rate`

### 20. Inspect Domain Diagnostics
- **Type:** Row
- **Purpose:** Collapsed row-based diagnostics workflow.
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

### 23. Review Processed Records — removed

Removed from Run Overview. Run Domains uses the wider left column; the compact
Selected Run Status and Run Identity panels occupy the right column.

### 24. Inspect Alerts
- **Type:** Row
- **Purpose:** Expanded alert/SLO evidence immediately after the first-level
  matrix. The visible `Status` (First Action снята, см. §4) retains the critical
  verdict and route, while this compact table exposes alert-level impact.
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
- Row-based workflows (Domain Status Tracks, Inspect Range Evidence, Inspect Domain Diagnostics, Inspect Alerts) provide structured triage paths.
- The full-width `Inputs` matrix is the deviation-first subsystem summary.
  Repeated Control Plane, Runtime, Data Quality, Provider, Data Validation, and
  Workflow mirrors live in the collapsed `Inspect Domain Diagnostics` row.
- `Inspect Alerts` is collapsed by default (first screen is Status +
  Domain Status; First Action снята намеренно, см. §4). L1 Historical Trends,
  Range Evidence, and Domain Diagnostics stay collapsed progressive disclosure.

## Additional shipped panels
### 27. Review All Domain Status

Shipped in `bioetl-overview-v2.json`.
### 28. Review Selected Run Status

Shipped in `bioetl-overview-v2.json`.
The table sits to the right of Review Run Domains and shows Processing,
Replay readiness, and a word-wrapped Reason. SUCCESS is green. Overall verdict
is displayed in its dedicated stat panel rather than repeated in this table.

### 100. Inspect Full First Action — removed from shipped JSON

Панель `id=20215` снята вместе с §4 (RF-006 #11257, issue #11809).

### 101. Inspect Full First Action — removed from shipped JSON

Панель `id=30215` снята вместе с §4 (RF-006 #11257, issue #11809).

## Saved evidence and discovery panels

| ID | Title | Purpose |
| --- | --- | --- |
| 9450 | Inspect Saved Run Evidence | Saved exact-run evidence; expand for identity, version, reasons and actions. |
| 9451 | Inspect Selected Run Domains | Saved exact-run evidence; expand for identity, version, reasons and actions. |
| 9452 | Inspect Selected Run Identity | Saved exact-run evidence; expand for identity, version, reasons and actions. |

<!-- BEGIN SHIPPED PANEL INVENTORY -->
## Current shipped panel inventory

Generated from the dashboard JSON. Earlier sections explain panel semantics; this table identifies the panels shipped in the current dashboard.

| ID | Title | Type |
| --- | --- | --- |
| 99 | Inspect Scope & Evidence | text |
| 9604 | Review Overall Verdict | stat |
| 9603 | Review Selected Run Status | table |
| 9002 | Review Run Domains | table |
| 9300 | Review Run Identity | table |
<!-- END SHIPPED PANEL INVENTORY -->
