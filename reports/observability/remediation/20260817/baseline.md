# Observability telemetry baseline — 2026-08-17

Tree: `origin/main` @ `3d2c68813e`.
Program: OBS-LIFE-001 / OBS-PROV-001 / OBS-DQ-001 (lifetime + projection).
Do not treat this file as a metric catalog; names stay in
`docs/04-reference/observability/metrics-catalog.md`.

## Artifact hashes

| Path | SHA-256 |
| --- | --- |
| `grafana/dashboards/bioetl-control-plane-v1.json` | `542da637ba292534d9c0825af2f731f4020449592996bb16d67d36b5525ac198` |
| `grafana/dashboards/bioetl-overview-v2.json` | `ccae22eb74ed628e3d0ccd1be551faca8e36864b90ebd347ceb3f4eeeeeffcb4` |
| `grafana/dashboards/bioetl-runtime.json` | `5cdd1b6d387be72c79f26479cee018f7fa03d43670743d7768c8ac321fe47011` |
| `grafana/dashboards/bioetl-provider-health-v2.json` | `72c5894ffc1836210c989942ab178cecf5baf4de81bc14d1c43fbf58020dd324` |
| `grafana/dashboards/bioetl-dq-v2.json` | `09d5a84b01e05a3dbd2cfd4a7aa7083caf9d140a6be4f35f507054a1c687d39b` |
| `grafana/dashboards/bioetl-incident-v1.json` | `33579f60669d0931a8e4aa5276ec75f21970d20a9e8fb8e447c889e9c0abd80d` |
| `grafana/dashboards/bioetl-run-explorer-v1.json` | `2f21ac921755224337ed0d8b192e430ee76b5cdd278ada94d08c455444d196fc` |
| `grafana/prometheus-rules/bioetl_observability.yml` | `b71ebfd0a20437c98378cbd2bbeacf50ba3b6cb43a889c5c0997cf1f78ed4662` |
| `grafana/prometheus-rules/bioetl_control_plane_current_status.yml` | `4e7b2869dea46fc3b83ffa8ecf8cc6f42be13a82b83779b6fe4f4f6f20216f2d` |

## Residual gap matrix

| ID | Metric / signal | Emit site | Flush | Rule | Panel consumer | Last proven sample |
| --- | --- | --- | --- | --- | --- | --- |
| OBS-LIFE-001 | `bioetl_pipeline_runs_total` | `PipelineObserver.__exit__` (canonical). `PipelineRunnerService` must not increment again. | `publish_metrics_safely` after accounting | `bioetl_runtime_trust_gap_status_10m` | Runtime / Overview status | fixture unit + promtool |
| OBS-LIFE-001 | `bioetl_records_processed_total` / `bioetl_stage_records_total` | `BatchMetricsRecorderService` + `track_transform_result_metrics` | same | processed-records recordings | Runtime / DQ / HTTP row 08 | fixture 1000/1000/983/17 |
| OBS-PROV-001 | `bioetl_health_check_*_total` | `HealthCheckProviderMixin.check_health` via `handle_health_check_result` | same | `bioetl_provider_health_check_provider_universe_15m` | Provider Health | Chembl mixin path only |
| OBS-PROV-001 | cached Bronze | `CachedBronzeDataSource.health_check` returns HEALTHY, no counters, no `provider=chembl` | n/a | n/a | must stay N/A, not OK | unit |
| OBS-DQ-001 | `bioetl_dq_current_reason` reason=`gold_contract_exclusions` | recording over gold `excluded_by_contract` | n/a | warn only | DQ current reason/status | promtool |

## Fixture contract

`chembl_assay` / `backfill`: Bronze 1000, Silver valid 1000, Gold written 983,
`excluded_by_contract` 17, quarantine 0.
Existing `pipeline_run_report_golden.json` (`chembl_activity` 1000/850/820/30/50)
is not a substitute.
