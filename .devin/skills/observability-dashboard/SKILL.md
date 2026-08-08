---
name: "observability-dashboard"
description: "Edit, render, validate, or debug BioETL Grafana dashboards and their PromQL panels without starting optional monitoring services unless requested."
---

# Observability Dashboard

## Source Of Truth

- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../docs/02-architecture/decisions`
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`
- Dashboard source: `../../../grafana/dashboards/`
- Render and validation scripts: `../../../scripts/`

## Environment Configuration

This skill uses Grafana credentials from the repository root `.env` file:

- `GRAFANA_URL` - Grafana server URL (default: http://localhost:3000)
- `GRAFANA_SERVICE_ACCOUNT_TOKEN` - Grafana service account token for API access
- `GRAFANA_USERNAME` - Grafana username (fallback auth)
- `GRAFANA_PASSWORD` - Grafana password (fallback auth)
- `GRAFANA_ORG_ID` - Grafana organization ID
- `GF_SECURITY_ADMIN_PASSWORD` - Admin password for local Grafana instance
- `GF_RENDERING_RENDERER_TOKEN` - Image renderer token
- `GRAFANA_IMAGE_RENDERER_GOMEMLIMIT` - Renderer memory limit
- `GRAFANA_IMAGE_RENDERER_READINESS_TIMEOUT` - Renderer readiness timeout

**Note:** Monitoring services are optional (ADR-010). Do not start `docker-compose.monitoring.yml`
unless the user explicitly requests dashboard/render work. Default Docker surface is main only
(health on :8000).

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
