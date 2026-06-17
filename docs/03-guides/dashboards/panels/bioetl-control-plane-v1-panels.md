# BioETL Control Plane v1 - Panels Documentation

**Dashboard file:** `grafana/dashboards/bioetl-control-plane-v1.json`

## Обзор

Dashboard `0. Control Plane` monitors replay safety, manifest/ledger integrity,
checkpoint freshness, audit activity, and lineage evidence. Shipped dashboard
JSON is the source of truth.

## Key Panels

### 1. Monitor: Replay Safety State
- **Type:** Stat
- **Purpose:** Current replay-safety verdict for the selected scope.
- **Data sources:** `bioetl_replay_safety_blockers_15m`

### 2. Monitor: Checkpoint Freshness Lag
- **Type:** Stat
- **Purpose:** Show seconds since the latest checkpoint save.
- **Data sources:** `bioetl_checkpoint_age_seconds`

### 3. Monitor: Manifest / Ledger Integrity
- **Type:** Stat
- **Purpose:** Flag manifest write and ledger append failures.
- **Data sources:** `bioetl_manifest_ledger_failures_15m`

### 4. Inspect: Telemetry Missing
- **Type:** Stat
- **Purpose:** Distinguish no data from missing control-plane telemetry.
- **Data sources:** `bioetl_control_plane_telemetry_missing_5m`

### 5. Replay / Resume Evidence
- **Type:** Stat / Timeseries
- **Purpose:** Track replay blockers, checkpoint compatibility, drift, and lag.
- **Data sources:** `bioetl_checkpoint_compatibility_events_total`,
  `bioetl_replay_reconstructability_events_total`,
  `bioetl_replay_drift_events_total`, `bioetl_replay_lag_seconds`,
  `bioetl_lineage_refs_missing_total`

### 6. Manifest, Ledger, Audit, and Read Paths
- **Type:** Stat / Timeseries / Table
- **Purpose:** Inspect control-plane persistence and query paths.
- **Data sources:** `bioetl_control_plane_manifest_writes_total`,
  `bioetl_control_plane_ledger_appends_total`,
  `bioetl_control_plane_reads_total`,
  `bioetl_control_plane_read_duration_seconds_bucket`,
  `bioetl_audit_write_events_total`, `bioetl_audit_query_events_total`,
  `bioetl_audit_write_duration_seconds_bucket`,
  `bioetl_audit_query_duration_seconds_bucket`

## Variables

- `workflow`, `pipeline`, `run_type`, and `run_id` are the shared primary
  dashboard context shell.

## Notes

- The control-plane status group is implemented by recording rules in
  `grafana/prometheus-rules/`, but the dashboard panels use declared recording
  outputs such as `bioetl_replay_safety_blockers_15m` and
  `bioetl_manifest_ledger_failures_15m`.
- Legacy placeholder metric names for generic run-manifest, ledger, workflow,
  and checkpoint operations are intentionally not documented here.
