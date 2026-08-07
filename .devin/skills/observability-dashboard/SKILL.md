---
name: "observability-dashboard"
description: "Edit, render, validate, or debug BioETL Grafana dashboards and their PromQL panels without starting optional monitoring services unless requested."
---

# Observability Dashboard

## Source Of Truth

- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Dashboard source: `../../../grafana/dashboards/`
- Render and validation scripts: `../../../scripts/`

## Workflow

1. Confirm that the task touches a shipped dashboard or asks for a render.
2. Inspect real metric names and labels before changing a query.
3. Use `mode=edit`, `render`, or `debug`; keep the default runtime local-only.
4. Do not start `docker-compose.monitoring.yml` unless the user explicitly
   requested dashboard/render work.
5. Validate JSON, queries, and relevant dashboard tests; update operator docs
   when shipped behaviour changes.

This single skill replaces `grafana-dashboard-extension`,
`grafana-dashboard-render`, `prometheus-metric-discovery`, and
`prometheus-query-debugger` for dashboard work.
