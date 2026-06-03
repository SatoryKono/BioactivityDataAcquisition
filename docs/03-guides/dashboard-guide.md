______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-03'

______________________________________________________________________

# Dashboard Guide

This guide is the current compact inventory for shipped Grafana dashboards.
Detailed monitoring setup remains in `grafana/README.md` and
[Metrics & Monitoring Guide](metrics-monitoring.md).

## Dashboard Inventory

| Dashboard | File | Primary purpose |
| --- | --- | --- |
| Control Plane | `grafana/dashboards/bioetl-control-plane-v1.json` | RunManifest, RunLedger, replay/control-plane health. |
| Overview | `grafana/dashboards/bioetl-overview-v2.json` | Pipeline and provider-level operator summary. |
| Runtime | `grafana/dashboards/bioetl-runtime.json` | Runtime durations, stages, throughput, record accounting. |
| Provider Health | `grafana/dashboards/bioetl-provider-health-v2.json` | Provider/API health and adapter status. |
| Data Quality | `grafana/dashboards/bioetl-dq-v2.json` | DQ score, validation failures, quarantine, anomalies. |
| Workflow Overview | `grafana/dashboards/bioetl-workflow-overview.json` | Workflow step and status projections. |
| Alerts & SLO | `grafana/dashboards/bioetl-alerts-slo.json` | Alert rule and SLO status. |
| Silver Reject Explorer | `grafana/dashboards/bioetl-silver-reject-explorer.json` | Silver filter rejects and quarantine drilldown. |

## Provisioning Surfaces

| Surface | File |
| --- | --- |
| Dashboard provisioning | `grafana/provisioning/dashboards/bioetl.yml` |
| Prometheus datasource | `grafana/provisioning/datasources/prometheus.yml` |
| Loki datasource | `grafana/provisioning/datasources/loki.yml` |
| Tempo datasource | `grafana/provisioning/datasources/tempo.yml` |
| Quarantine Explorer datasource | `grafana/provisioning/datasources/quarantine-explorer.yml` |
| Prometheus rules | `grafana/prometheus-rules/*.yml` |

## Validation

Preferred checks:

```bash
python -m scripts.ops check-grafana-audit-preflight
python -m scripts.ops audit-live-grafana
python -m scripts.ops rerender-grafana
```

Use `bash scripts/ops/observability/grafana/setup_grafana_screenshot_runtime.sh`
on Linux/WSL hosts when Playwright/Chromium runtime libraries are missing.

## Design Constraints

- Dashboards are source-controlled JSON under `grafana/dashboards/`.
- Dashboard behavior must match live metric families registered/emitted by
  `src/bioetl/infrastructure/observability/`.
- PromQL and panel labels must preserve bounded-label policy from
  [Observability Guide](observability-guide.md).
