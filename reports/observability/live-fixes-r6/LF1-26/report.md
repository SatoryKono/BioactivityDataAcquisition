# LF1-26 TELEMETRY MISSING classification

Issue: #12822.

- Source SHA: `48dc0257ed980decaf0d8bf4c209c7e39309a4c4` (`origin/main`).
- Observation UTC: `2026-11-09T08:36:29Z`.
- A rendered Grafana snapshot was not available (`docker` is absent; Grafana and Prometheus were not started). The list below is every shipped panel whose `noValue` starts with `TELEMETRY MISSING`, from the five dashboard JSON files. Other panels mention the phrase only in a description and keep a different `noValue`.
- Local process scrape: `GET http://127.0.0.1:8000/metrics`. This is not a Prometheus range evaluation.

## Panels

All 15 panels are on `bioetl-incident-v1`. None of their expressions contain `or vector(0)`. `run_id` is not used as a Prometheus label in these expressions. Expected evidence follows the scope of each expression. Panel 238 filters by run type. Panels 256, 908, 8805, 8807, and 112 filter by pipeline. Panels 241, 240, 131, and 135 filter by both pipeline and run type. Panels 8806, 209, 210, 107, and 108 query global series without pipeline, run type, or workflow filters. An absent series is `TELEMETRY MISSING`, not zero. A query failure is outside this `noValue` and was not rendered.

| Panel | Title | Metric family on local scrape | Samples | Class |
| --- | --- | --- | --- | --- |
| 238 | Track Stage Backlog Trend | `bioetl_stage_backlog_records` | 0 | absent series on this process; display contract, not a zero |
| 256 | Review Errors by Stage & Code | `bioetl_errors_total` | 0 | absent series on this process; display contract, not a zero |
| 241 | Compare Records by Stage & Run Type | `bioetl_records_processed_total` | 0 | absent series on this process; display contract, not a zero |
| 240 | Track Records by Stage / Interval | `bioetl_records_processed_total` | 0 | absent series on this process; display contract, not a zero |
| 908 | Review Observed Terminal Counters | `bioetl_control_plane_terminal_events_total` | 0 | absent series on this process; display contract, not a zero |
| 8806 | Compare Global Reads by Store | `bioetl_control_plane_reads_total` | 4 | source family present locally; PromQL panel result `NOT_VERIFIABLE` |
| 209 | Track Global Shutdown Starts | `bioetl_shutdown_initiated_total` | 0 | absent series on this process; display contract, not a zero |
| 210 | Track Global Shutdown Completions | `bioetl_shutdown_completed_total` | 0 | absent series on this process; display contract, not a zero |
| 131 | Track Observed Manifest Write Increments | `bioetl_control_plane_manifest_writes_total` | 0 | absent series on this process; display contract, not a zero |
| 107 | Compare Global Audit Write Outcomes | `bioetl_audit_write_events_total` | 0 | absent series on this process; display contract, not a zero |
| 8805 | Compare Checkpoint Outcomes | `bioetl_checkpoint_compatibility_events_total` | 0 | absent series on this process; display contract, not a zero |
| 108 | Compare Global Audit Query Outcomes | `bioetl_audit_query_events_total` | 0 | absent series on this process; display contract, not a zero |
| 135 | Track Replay Lag | `bioetl_replay_lag_seconds` | 0 | absent series on this process; display contract, not a zero |
| 8807 | Compare Ledger Appends by Type & Status | `bioetl_control_plane_ledger_appends_total` | 0 | absent series on this process; display contract, not a zero |
| 112 | Compare Lineage Persistence Outcomes | `bioetl_lineage_fragments_emitted_total` | 0 | absent series on this process; display contract, not a zero |

The four `bioetl_control_plane_reads_total` samples are manifest `list_all` misses on this process. They do not establish a non-empty Prometheus range for the global query in panel 8806. Zero samples mean the family emitted no series here. That is not a measured zero and not a display defect: the panel `noValue` already says the missing series is not a zero.

Overview, Data Quality, Run Explorer and Replay Readiness have no `noValue` that starts with `TELEMETRY MISSING` in this SHA.

## Decision

No generator change. Missing series were not rewritten to `or vector(0)` or to a fake success value.

## Checklist

- Each panel in the `noValue` list has a class. On-screen Grafana text is `NOT_VERIFIABLE`.
- Missing series stay distinct from zero. Prometheus itself is unavailable, so range results stay `NOT_VERIFIABLE` rather than PASS.
- Evidence is this report, the receipt and checksums. Deploy SHA is `NOT_VERIFIABLE`.
