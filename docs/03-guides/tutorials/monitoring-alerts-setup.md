______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# Tutorial: Monitoring and Alerts Setup

**Issue:** #6541
**Runtime:** Local-Only by default ([ADR-010](../../02-architecture/decisions/ADR-010-local-only-deployment.md)).
Grafana/Prometheus are **optional**.

## Stack overview

| Component | Role | Required? |
| --- | --- | --- |
| Structured logs | ADR-017 / ADR-019 | Yes (local) |
| Metrics emission | Pipeline, DQ, HTTP | Yes for metrics path |
| Prometheus scrape | Collection | Optional |
| Grafana dashboards | Operator UX | Optional |
| Alert rules | Prometheus/Grafana | Optional |

Deep guides: [metrics-monitoring.md](../metrics-monitoring.md),
[observability-guide.md](../observability-guide.md),
[dashboard-guide.md](../dashboard-guide.md).

## Local path (no monitoring Docker)

1. Run a small pipeline; confirm logs include `run_id` / pipeline identity.
2. Confirm metrics emission for your process (exporter flags/env in metrics guide).
3. Prefer CLI + run-manifest inspection before dashboards.
4. DQ failures: [pipeline-failure-dq](../../05-operations/runbooks/pipeline-failure-dq.md).

## Optional Grafana path

Only when the task explicitly needs dashboards:

1. Shipped JSON under `grafana/dashboards/*.json` is SSOT.
2. Skills: `grafana-dashboard-render`, `grafana-dashboard-extension`.
3. Panel docs: `docs/03-guides/dashboards/panels/`.
4. Do **not** start `docker-compose.monitoring.yml` unless requested (AGENTS.md).

## Alert classes

| Class | First response |
| --- | --- |
| Pipeline failure | [pipeline-failure-critical](../../05-operations/runbooks/pipeline-failure-critical.md) |
| DQ hard fail | [pipeline-failure-dq](../../05-operations/runbooks/pipeline-failure-dq.md) |
| HTTP / resilience | ADR-032 + adapter logs |
| Stale success / freshness | schedule + control-plane review |

## Verification

- [ ] Successful local run with run identity in logs
- [ ] Metrics path known for deployment mode
- [ ] If Grafana used: one shipped dashboard opens with expected datasource
- [ ] Rule file edits validated with `promtool` when applicable

## Related

- [Prometheus metrics export](../prometheus-metrics-export.md)
- [Grafana dashboard configuration](../grafana-dashboard-configuration.md)
