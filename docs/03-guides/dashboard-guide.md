______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-19'

______________________________________________________________________

# Dashboard Guide

This guide is the operator/contributor orientation page for shipped Grafana
dashboards.

Canonical shipped inventory and versioning policy now live in
[dashboards/dashboard-inventory.md](dashboards/dashboard-inventory.md).
Detailed monitoring setup remains in `grafana/README.md` and
[Metrics & Monitoring Guide](metrics-monitoring.md).

## Canonical Reading Order

1. [dashboards/dashboard-inventory.md](dashboards/dashboard-inventory.md) for
   shipped JSON -> docs -> datasource -> versioning mapping
2. [dashboards/monitoring-index.md](dashboards/monitoring-index.md) for
   incident-time routing
3. [dashboards/dashboard-v2-usage.md](dashboards/dashboard-v2-usage.md) for
   operational usage and triage semantics
4. panel-specific pages under `dashboards/panels/` for formula- and
   panel-level detail

## Provisioning Surfaces

| Surface | File |
| --- | --- |
| Dashboard provisioning | `grafana/provisioning/dashboards/bioetl.yaml` |
| Prometheus datasource | `grafana/provisioning/datasources-core/prometheus.yml` |
| Quarantine Explorer datasource | `grafana/provisioning/datasources-core/quarantine-explorer.yml` |
| Loki datasource | `grafana/provisioning/datasources-tracing/loki.yml` |
| Tempo datasource | `grafana/provisioning/datasources-tracing/tempo.yml` |
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
- Human-readable dashboard inventory must stay aligned with
  `docs/03-guides/dashboards/contracts/dashboard-inventory.yaml`.
- PromQL and panel labels must preserve bounded-label policy from
  [Observability Guide](observability-guide.md).
