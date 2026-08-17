# BioETL Control Plane v1 - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-control-plane-v1.json`

## Обзор

Dashboard `0. Control Plane` monitors replay safety, manifest/ledger integrity,
checkpoint freshness, explicit checkpoint/manifest/lineage validation, retention
compliance, bounded failure reasons, audit activity, and lineage evidence.
Shipped dashboard JSON is the source of truth.

Diagnostic failure, incompatibility, replay, and lineage panels preserve empty
Prometheus results as `No data`/`UNKNOWN`; they do not synthesize zero. A visible
zero is therefore evidence from a present series, not proof inferred from metric
absence.

## Variable contract

- All panels inherit the shared shell selectors: `workflow`, `pipeline`,
  `run_type`, `run_id`.
- Prometheus summary panels normalize the selected `pipeline` when the metric
  family stores workflow-prefixed pipeline labels.
- `BioETL Ops HTTP` table/stat panels depend on the detached HTTP control
  plane backend rather than Prometheus.

## Panel inventory

### Dashboard shell

| ID | Title | Type | Datasource | Query / purpose | Variables | Thresholds / drilldown |
| --- | --- | --- | --- | --- | --- | --- |
| 9400 | Inspect Scope & Evidence | text | Static | Replay-safety question: SELECTED RUN is this run's processing outcome and Trust status; CURRENT is pipeline replay readiness now, not this run. INCOMPLETE/UNKNOWN is incomplete evidence, not OK. | shared shell | No thresholds; interpretive guidance only. |
| 9401 | Monitor Replay Readiness | stat | Prometheus | CURRENT Prometheus replay/resume verdict from `bioetl_control_plane_current_status_trusted` (not selected-run HTTP trust). | shared shell | `0=OK`, `1=WARN`, `2=CRIT`, `3=INCOMPLETE`, `null=UNKNOWN`. `INCOMPLETE` blocks Prom-current replay approval. |
| 9418 | Review Selected-Run Trust | table | BioETL Ops HTTP | Exact-run `processing_status`, `trust_status`, `scope_kind`, and `evidence_freshness` from manifest-validation. | shared shell | `INCOMPLETE`/`ERROR`/`UNAVAILABLE` are not OK. |
| 9402 | Review Run Summary | table | BioETL Ops HTTP | Identity anchors for the selected workflow/pipeline/run scope. | shared shell | No numeric threshold; forensic handoff table. |
| 9403 | Review Processed Records | table | BioETL Ops HTTP | Current processed-record evidence for the selected run scope. | shared shell | No numeric threshold; read-path evidence table. |
| 9410 | Explain Missing Identity Data | text | Static | Neutral visible fallback when the Control Plane identity table returns no visible rows. | shared shell | No thresholds; prevents blank first-screen identity space. |
| 9411 | Explain Missing Record Counts | text | Static | Neutral visible fallback when the Control Plane accounting table returns no visible rows. | shared shell | No thresholds; distinguishes missing accounting evidence from zero records. |
| 891 | Monitor Replay Safety | stat | Prometheus | Replay-safety blocker state for the selected scope. | shared shell | Severity/value mapping. |
| 892 | Monitor Checkpoint Age | stat | BioETL Ops HTTP | Current checkpoint freshness lag from HTTP-backed control-plane evidence. | shared shell | Numeric lag; no PromQL threshold in doc. |
| 893 | Monitor Manifest/Ledger | stat | Prometheus | Current manifest/ledger failure state from `bioetl_manifest_ledger_failures_15m`. | shared shell | Severity/value mapping. |
| 907 | Monitor Telemetry | stat | Prometheus | Missing-control-plane-telemetry signal from `bioetl_control_plane_telemetry_missing_5m`. | shared shell | Value mapping distinguishes no-data vs telemetry-missing. |
| 906 | Review Recovery Action | text | Static | Next-step rail: do not replay this run if Trust status is INCOMPLETE or UNKNOWN; look at Review Selected-Run Trust below, then expand Inspect Audit & Lineage Evidence. | shared shell | Links: 130 blockers, 9418 this-run Trust, 9415 lineage, 9416 retention. |

### Inspect Replay & Checkpoint Evidence

| ID | Title | Type | Datasource | Query / purpose | Variables | Thresholds / drilldown |
| --- | --- | --- | --- | --- | --- | --- |
| 902 | Inspect Replay & Checkpoint Evidence | row | Static | Collapsed-by-default incident section for checkpoint/replay safety evidence. | shared shell | Expand only after the first-screen verdict points to replay/checkpoint evidence. |
| 894 | Review Coverage Limits | text | Static | Static explanation of expected-empty and backend caveat cases. | shared shell | No thresholds; interpretive guidance only. |
| 130 | Track Replay Blockers | stat | Prometheus | Selected-range blocker rollup across manifest, ledger, replay, and checkpoint failure families. | shared shell | Count panel; no separate threshold mapping documented. |
| 3 | Track Checkpoint Incompatibilities | stat | Prometheus | Incompatible checkpoint compatibility events from `bioetl_checkpoint_compatibility_events_total`. | shared shell | Count panel. |
| 104 | Track Unreconstructable Replays | stat | Prometheus | `bioetl_replay_reconstructability_events_total` with `status="not_reconstructable"`. | shared shell | Count panel. |
| 120 | Track Replay Drift | stat | Prometheus | Replay drift events from `bioetl_replay_drift_events_total`. | shared shell | Count panel. |
| 101 | Track Checkpoint Load Failures | stat | Prometheus | Failed checkpoint load events over the selected range. | shared shell | Count panel. |
| 102 | Track Checkpoint Save Failures | stat | Prometheus | Failed checkpoint save events over the selected range. | shared shell | Count panel. |
| 103 | Track Global Checkpoint Admin Failures | stat | Prometheus | Global checkpoint operator failures independent of pipeline scope. | shared shell | Count panel. |
| 121 | Track Peak Replay Lag | stat | Prometheus | Max replay lag for the selected scope from `bioetl_replay_lag_seconds`. | shared shell | Numeric lag panel. |
| 5 | Compare Checkpoint Outcomes | timeseries | Prometheus | Compatibility outcomes by `disposition` over time. | shared shell | Series legend is the primary mapping. |
| 134 | Track Replay Drift by Type | timeseries | Prometheus | Replay drift events by `replay_capability`, `drift_type`, and `status`. | shared shell | Series legend is the primary mapping. |
| 135 | Track Replay Lag | timeseries | Prometheus | Replay lag trend by replay capability and status. | shared shell | Time trend; no static threshold in doc. |
| 105 | Track Checkpoint Save Latency | timeseries | Prometheus | Histogram quantiles for checkpoint save latency. | shared shell | Quantile series `p50/p95/p99` are the key mapping. |
| 106 | Track Global Checkpoint Admin Latency | timeseries | Prometheus | Histogram quantiles for global checkpoint operator latency. | shared shell | Quantile series `p50/p95/p99` are the key mapping. |
| 9413 | Review Checkpoint Validation | table | BioETL Ops HTTP | Run-scoped parse, schema, checksum, and required-anchor checks with stable reason codes. | shared shell | `OK/WARNING/ERROR/UNKNOWN`; `UNKNOWN` never implies a healthy zero. |

### Inspect Manifest & Ledger Evidence

| ID | Title | Type | Datasource | Query / purpose | Variables | Thresholds / drilldown |
| --- | --- | --- | --- | --- | --- | --- |
| 901 | Inspect Manifest & Ledger Evidence | row | Static | Collapsed-by-default manifest/ledger incident section. | shared shell | Groups integrity panels; no direct metric. |
| 908 | Review Terminal Run Outcomes | table | Prometheus | Terminal run-event totals by `terminal_status`. | shared shell | Forensic table; status breakdown is the key mapping. |
| 1 | Track Manifest Write Failures | stat | Prometheus | Failed manifest writes over the selected range. | shared shell | Count panel. |
| 2 | Track Ledger Append Failures | stat | Prometheus | Failed ledger appends over the selected range. | shared shell | Count panel. |
| 131 | Compare Manifest Writes by Status | timeseries | Prometheus | Manifest writes by `status` and `run_type` over time. | shared shell | Series legend maps status/run type. |
| 7 | Compare Ledger Appends by Type & Status | timeseries | Prometheus | Ledger appends by `event_type` and `status`. | shared shell | Series legend maps event/status breakdown. |
| 132 | Monitor Manifest Failures (30m) | stat | Prometheus | 30-minute manifest write failure ratio severity. | shared shell | Threshold/value mapping encodes ratio severity. |
| 133 | Monitor Ledger Failures (30m) | stat | Prometheus | 30-minute ledger append failure ratio severity. | shared shell | Threshold/value mapping encodes ratio severity. |
| 9414 | Review Manifest Validation | table | BioETL Ops HTTP | Run-scoped parse, schema, schema-version, and contract-compatibility checks with stable reason codes. | shared shell | `OK/WARNING/ERROR/UNKNOWN`; unsupported schema versions are explicit. |

### Inspect Global Store Reliability

| ID | Title | Type | Datasource | Query / purpose | Variables | Thresholds / drilldown |
| --- | --- | --- | --- | --- | --- | --- |
| 903 | Inspect Global Store Reliability | row | Static | Collapsed-by-default global store-read reliability section. | shared shell | Groups global read panels; no direct metric. |
| 4 | Track Global Read Failures | stat | Prometheus | Failed control-plane reads across stores/operations. | shared shell | Count panel. |
| 136 | Monitor Global Read Failures (30m) | stat | Prometheus | 30-minute failure-ratio severity for global control-plane reads. | shared shell | Threshold/value mapping encodes severity bands. |
| 6 | Compare Global Reads by Store | timeseries | Prometheus | Read outcomes by `store`, `operation`, and `status`. | shared shell | Series legend is the key mapping. |
| 111 | Track Global Read Latency | timeseries | Prometheus | Histogram quantiles for successful control-plane read latency. | shared shell | Quantile series `p50/p95/p99` are the key mapping. |

### Inspect Audit & Lineage Evidence

| ID | Title | Type | Datasource | Query / purpose | Variables | Thresholds / drilldown |
| --- | --- | --- | --- | --- | --- | --- |
| 904 | Inspect Audit & Lineage Evidence | row | Static | Collapsed-by-default audit/lineage evidence section. | shared shell | Groups lineage and audit panels; no direct metric. |
| 122 | Track Missing Lineage References | stat | Prometheus | Missing lineage reference count over the selected range. | shared shell | Count panel. |
| 137 | Track Lineage Persistence Failures | stat | Prometheus | Failed lineage fragment persistence events. | shared shell | Count panel. |
| 138 | Review Missing Lineage by Layer | table | Prometheus | Missing lineage references grouped by `layer` and `ref_type`. | shared shell | Forensic table; grouped breakdown is the key mapping. |
| 107 | Compare Global Audit Write Outcomes | timeseries | Prometheus | Audit write events by `layer`, `operation`, and `status`. | shared shell | Series legend maps layer/operation/status. |
| 108 | Compare Global Audit Query Outcomes | timeseries | Prometheus | Audit query events by `layer_filter` and `status`. | shared shell | Series legend maps query outcome families. |
| 109 | Track Global Audit Write Latency | timeseries | Prometheus | Histogram quantiles for audit write latency. | shared shell | Quantile series `p50/p95/p99` are the key mapping. |
| 110 | Track Global Audit Query Latency | timeseries | Prometheus | Histogram quantiles for audit query latency. | shared shell | Quantile series `p50/p95/p99` are the key mapping. |
| 112 | Compare Lineage Persistence Outcomes | timeseries | Prometheus | Lineage fragment emission outcomes by `layer` and `status`. | shared shell | Series legend maps lineage outcome families. |
| 9415 | Review Lineage Validation | table | BioETL Ops HTTP | Run-scoped closure, identity-consistency, cycle-detection, and persistence-profile checks. | shared shell | Stable reason codes localize broken references, conflicts, and cycles. |
| 9416 | Review Retention Compliance | table | BioETL Ops HTTP | Run-scoped evidence-floor, retention-policy, required-evidence, and archive-support checks. | shared shell | Unsupported archive behavior is explicit rather than inferred as compliant. |

### Inspect Run Identity Evidence

| ID | Title | Type | Datasource | Query / purpose | Variables | Thresholds / drilldown |
| --- | --- | --- | --- | --- | --- | --- |
| 905 | Inspect Run Identity Evidence | row | Static | Collapsed identity-evidence and handoff section; the copyable identity anchor panels `9404` and `9407` remain above it on the first path. | shared shell | Groups remaining BioETL Ops HTTP evidence without replacing the first-screen replay/resume summary. |
| 9404 | Review Identity Anchors | table | BioETL Ops HTTP | Compact forensic identity anchors for the selected scope; use after ID, Replay Safety, Checkpoint Freshness, Manifest/Ledger, and Telemetry summary cards. | shared shell | Forensic handoff table. |
| 9405 | Review Identity Gaps | table | BioETL Ops HTTP | Compact missing identity surface inventory for the selected scope. | shared shell | Gap table; no numeric threshold. |
| 9406 | Compare Checkpoint Anchors | table | BioETL Ops HTTP | Compact side-by-side checkpoint anchor comparison. | shared shell | Comparison table; operator drilldown surface. |
| 9407 | Inspect Identity Values | table | BioETL Ops HTTP | Compact copy-ready IDs/anchors for incident handoff. | shared shell | Handoff table only. |
| 9408 | Review Required Replay Anchors | table | BioETL Ops HTTP | Compact priority replay/evidence anchors for first-line investigation. | shared shell | Incident handoff table. |
| 9409 | Review Additional Forensic Anchors | table | BioETL Ops HTTP | Compact secondary forensic anchors for deeper analysis. | shared shell | Incident handoff table. |
| 139 | Review Uncovered Replay Signals | text | Static | Static reminder of residual replay-safety signals to inspect after core blockers. | shared shell | No thresholds; review checklist only. |

### Run context (thin) -> Run Explorer hub

| ID | Title | Type | Datasource | Query / purpose | Variables | Thresholds / drilldown |
| --- | --- | --- | --- | --- | --- | --- |
| 9412 | Inspect Run Details | row | Static | Collapsed selected-run identity and processed-record evidence. | shared shell | Groups HTTP-backed evidence; no direct threshold. |
| 9417 | Review Bounded Failure Reasons | table | BioETL Ops HTTP | Selected-run failure counts mapped only to `api`, `dq`, `schema`, `storage`, `network`, `validation`, and `unknown`. | shared shell | Raw messages and high-cardinality identifiers are excluded. |

## PromQL Formula Anchors

The shipped dashboard JSON remains the byte-level source of truth. The formulas
below document the current Prometheus query families for all Prometheus-backed
panels; HTTP-backed identity panels are documented in the inventory above.

- `Status`: `max((bioetl_control_plane_current_status_trusted{run_type=~"$run_type"}) and on(pipeline) label_replace(label_replace(vector(1), "pipeline_raw", "$pipeline", "", ""), "pipeline", "$1", "pipeline_raw", "^(?:workflow_)?(.*)$"))`
- `Monitor Replay Safety`: `max((bioetl_replay_safety_blockers_15m{run_type=~"$run_type"}) and on(pipeline) label_replace(label_replace(vector(1), "pipeline_raw", "$pipeline", "", ""), "pipeline", "$1", "pipeline_raw", "^(?:workflow_)?(.*)$"))`
- `Monitor Manifest/Ledger`: `max((bioetl_manifest_ledger_failures_15m{run_type=~"$run_type"}) and on(pipeline) label_replace(label_replace(vector(1), "pipeline_raw", "$pipeline", "", ""), "pipeline", "$1", "pipeline_raw", "^(?:workflow_)?(.*)$"))`
- `Monitor Telemetry`: `max((bioetl_control_plane_telemetry_missing_5m{run_type=~"$run_type"}) and on(pipeline) label_replace(label_replace(vector(1), "pipeline_raw", "$pipeline", "", ""), "pipeline", "$1", "pipeline_raw", "^(?:workflow_)?(.*)$"))`
- `Track: Replay / Resume Blockers in Range`: `round((sum(increase(bioetl_control_plane_manifest_writes_total{pipeline=~"$pipeline", run_type=~"$run_type", status="failed"}[$__range])) or vector(0)) + (sum(increase(bioetl_control_plane_ledger_appends_total{pipeline=~"$pipeline", status="failed"}[$__range])) or vector(0)) + (sum(increase(bioetl_checkpoint_compatibility_events_total{pipeline=~"$pipeline", disposition=~".*_incompatible"}[$__range])) or vector(0)) + (sum(increase(bioetl_replay_reconstructability_events_total{pipeline=~"$pipeline", status="not_reconstructable"}[$__range])) or vector(0)) + (sum(increase(bioetl_replay_drift_events_total{pipeline=~"$pipeline", run_type=~"$run_type"}[$__range])) or vector(0)) + (sum(increase(bioetl_lineage_refs_missing_total{pipeline=~"$pipeline"}[$__range])) or vector(0)))`
- `Monitor: Checkpoint Incompatibilities`: `round(sum(increase(bioetl_checkpoint_compatibility_events_total{pipeline=~"$pipeline", disposition=~".*_incompatible"}[$__range])) or vector(0))`
- `Monitor: Replay Not Reconstructable`: `round(sum(increase(bioetl_replay_reconstructability_events_total{pipeline=~"$pipeline", status="not_reconstructable"}[$__range])) or vector(0))`
- `Monitor: Replay Drift`: `round(sum(increase(bioetl_replay_drift_events_total{pipeline=~"$pipeline", run_type=~"$run_type"}[$__range])) or vector(0))`
- `Monitor: Checkpoint Load Failures`: `round(sum(increase(bioetl_checkpoint_load_events_total{pipeline=~"$pipeline", status="failed"}[$__range])) or vector(0))`
- `Monitor: Checkpoint Save Failures`: `round(sum(increase(bioetl_checkpoint_save_events_total{pipeline=~"$pipeline", status="failed"}[$__range])) or vector(0))`
- `Monitor: GLOBAL Checkpoint Operator Failures`: `round(sum(increase(bioetl_checkpoint_operator_operations_total{status="failed"}[$__range])) or vector(0))`
- `Track: Replay Lag Seconds`: `max(max_over_time(bioetl_replay_lag_seconds{pipeline=~"$pipeline", run_type=~"$run_type"}[$__range]))`
- `Track: Checkpoint Compatibility Outcomes`: `sum by (disposition) (increase(bioetl_checkpoint_compatibility_events_total{pipeline=~"$pipeline"}[$__interval])) or label_replace(vector(0), "disposition", "no_events", "", "")`
- `Track: Replay Drift by Type`: `sum by (replay_capability, drift_type, status) (increase(bioetl_replay_drift_events_total{pipeline=~"$pipeline", run_type=~"$run_type"}[$__interval]))`
- `Track: Replay Lag Trend`: `max by (replay_capability, status) (bioetl_replay_lag_seconds{pipeline=~"$pipeline", run_type=~"$run_type"})`
- `Track: Checkpoint Save Latency p50`: `histogram_quantile(0.50, sum by (le, pipeline, operation) (increase(bioetl_checkpoint_save_duration_seconds_bucket{pipeline=~"$pipeline"}[$__range])))`
- `Track: Checkpoint Save Latency p95`: `histogram_quantile(0.95, sum by (le, pipeline, operation) (increase(bioetl_checkpoint_save_duration_seconds_bucket{pipeline=~"$pipeline"}[$__range])))`
- `Track: Checkpoint Save Latency p99`: `histogram_quantile(0.99, sum by (le, pipeline, operation) (increase(bioetl_checkpoint_save_duration_seconds_bucket{pipeline=~"$pipeline"}[$__range])))`
- `Track: GLOBAL Checkpoint Operator Latency p50`: `histogram_quantile(0.50, sum by (le, operation) (increase(bioetl_checkpoint_operator_duration_seconds_bucket[$__range])))`
- `Track: GLOBAL Checkpoint Operator Latency p95`: `histogram_quantile(0.95, sum by (le, operation) (increase(bioetl_checkpoint_operator_duration_seconds_bucket[$__range])))`
- `Track: GLOBAL Checkpoint Operator Latency p99`: `histogram_quantile(0.99, sum by (le, operation) (increase(bioetl_checkpoint_operator_duration_seconds_bucket[$__range])))`
- `Inspect: Terminal Run Events by Status in Range`: `sum by (terminal_status) (increase(bioetl_control_plane_terminal_events_total{pipeline=~"$pipeline"}[$__range]))`
- `Monitor: Manifest Write Failures`: `round(sum(increase(bioetl_control_plane_manifest_writes_total{pipeline=~"$pipeline", run_type=~"$run_type", status="failed"}[$__range])) or vector(0))`
- `Monitor: Ledger Append Failures`: `round(sum(increase(bioetl_control_plane_ledger_appends_total{pipeline=~"$pipeline", status="failed"}[$__range])) or vector(0))`
- `Track: Manifest Writes by Status`: `sum by (status, run_type) (increase(bioetl_control_plane_manifest_writes_total{pipeline=~"$pipeline", run_type=~"$run_type"}[$__interval]))`
- `Track: Ledger Appends by Event Type / Status`: `sum by (event_type, status) (increase(bioetl_control_plane_ledger_appends_total{pipeline=~"$pipeline"}[$__interval]))`
- `Monitor: Manifest Write Failure Ratio`: `((sum(increase(bioetl_control_plane_manifest_writes_total{pipeline=~"$pipeline", run_type=~"$run_type", status="failed"}[30m])) or vector(0)) / clamp_min((sum(increase(bioetl_control_plane_manifest_writes_total{pipeline=~"$pipeline", run_type=~"$run_type"}[30m])) or vector(0)), 1))` mapped to WARN/CRIT bands.
- `Monitor: Ledger Append Failure Ratio`: `((sum(increase(bioetl_control_plane_ledger_appends_total{pipeline=~"$pipeline", status="failed"}[30m])) or vector(0)) / clamp_min((sum(increase(bioetl_control_plane_ledger_appends_total{pipeline=~"$pipeline"}[30m])) or vector(0)), 1))` mapped to WARN/CRIT bands.
- `Monitor: GLOBAL Control-Plane Read Failures`: `round(sum(increase(bioetl_control_plane_reads_total{status="failed"}[$__range])) or vector(0))`
- `Monitor: GLOBAL Control-Plane Read Failure Ratio Severity`: `((sum(increase(bioetl_control_plane_reads_total{status="failed"}[30m])) or vector(0)) / clamp_min((sum(increase(bioetl_control_plane_reads_total[30m])) or vector(0)), 1))` mapped to WARN/CRIT bands.
- `Track: GLOBAL Control-Plane Reads by Store / Operation / Status`: `sum by (store, operation, status) (increase(bioetl_control_plane_reads_total[$__interval]))`
- `Track: GLOBAL Control-Plane Read Latency p50`: `histogram_quantile(0.50, sum by (le) (increase(bioetl_control_plane_read_duration_seconds_bucket{status!="failed"}[$__range])))`
- `Track: GLOBAL Control-Plane Read Latency p95`: `histogram_quantile(0.95, sum by (le) (increase(bioetl_control_plane_read_duration_seconds_bucket{status!="failed"}[$__range])))`
- `Track: GLOBAL Control-Plane Read Latency p99`: `histogram_quantile(0.99, sum by (le) (increase(bioetl_control_plane_read_duration_seconds_bucket{status!="failed"}[$__range])))`
- `Monitor: Lineage Refs Missing`: `round(sum(increase(bioetl_lineage_refs_missing_total{pipeline=~"$pipeline"}[$__range])) or vector(0))`
- `Monitor: Lineage Fragment Persistence Failures`: `round(sum(increase(bioetl_lineage_fragments_emitted_total{pipeline=~"$pipeline", status="failed"}[$__range])) or vector(0))`
- `Inspect: Missing Lineage Refs by Layer / Type`: `sum by (layer, ref_type) (increase(bioetl_lineage_refs_missing_total{pipeline=~"$pipeline"}[$__range]))`
- `Track: GLOBAL Audit Write Outcomes`: `round(sum by (layer, operation, status) (increase(bioetl_audit_write_events_total[$__interval])) or vector(0))`
- `Track: GLOBAL Audit Query Outcomes`: `round(sum by (layer_filter, status) (increase(bioetl_audit_query_events_total[$__interval])) or vector(0))`
- `Track: GLOBAL Audit Write Latency p50`: `histogram_quantile(0.50, sum by (le) (increase(bioetl_audit_write_duration_seconds_bucket[$__range])))`
- `Track: GLOBAL Audit Write Latency p95`: `histogram_quantile(0.95, sum by (le) (increase(bioetl_audit_write_duration_seconds_bucket[$__range])))`
- `Track: GLOBAL Audit Write Latency p99`: `histogram_quantile(0.99, sum by (le) (increase(bioetl_audit_write_duration_seconds_bucket[$__range])))`
- `Track: GLOBAL Audit Query Latency p50`: `histogram_quantile(0.50, sum by (le) (increase(bioetl_audit_query_duration_seconds_bucket[$__range])))`
- `Track: GLOBAL Audit Query Latency p95`: `histogram_quantile(0.95, sum by (le) (increase(bioetl_audit_query_duration_seconds_bucket[$__range])))`
- `Track: GLOBAL Audit Query Latency p99`: `histogram_quantile(0.99, sum by (le) (increase(bioetl_audit_query_duration_seconds_bucket[$__range])))`
- `Track: Lineage Fragment Outcomes`: `sum by (layer, status) (increase(bioetl_lineage_fragments_emitted_total{pipeline=~"$pipeline"}[$__interval]))`

## Notes

- `Monitor Replay Safety` remains one business-signal card. `Status` is
  intentionally stricter: it reads `bioetl_control_plane_current_status_trusted`
  so replay blockers cannot render green when checkpoint evidence is missing or
  stale (`>=900s` WARN, `>=3600s` CRIT) or required telemetry is incomplete.
- `Checkpoint Freshness Lag`, `ID`, `Processed Records`, and the identity
  evidence tables are HTTP-backed `BioETL Ops HTTP` surfaces rather than
  Prometheus metric panels.
- Thresholds and value mappings not spelled out above should be taken from the
  shipped panel JSON; this page documents the panel inventory, datasource
  family, primary PromQL formulas, and operator purpose 1:1.
