---
name: "observability-dashboard"
description: "Edit, render, validate, or debug BioETL Grafana dashboards and their PromQL panels without starting optional monitoring services unless requested."
---

# Observability Dashboard

## Source Of Truth

- Normative index: `../../../docs/00-project/NORMATIVE_SOURCES.md`
- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../docs/02-architecture/decisions`
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`
- Dashboard source: `../../../grafana/dashboards/`
- Render and validation scripts: `../../../scripts/`

## Workflow

1. Confirm that the task touches a shipped dashboard or asks for a render.
2. Inspect real metric names and labels before changing a query.
3. Use `mode=edit`, `render`, or `debug`; keep the default runtime local-only.
4. Do not start `docker-compose.monitoring.yml` unless the user explicitly
   requested dashboard/render work.
5. Validate JSON, queries, and relevant dashboard tests; update operator docs
   when shipped behaviour changes. Any change under `grafana/dashboards/`
   MUST run
   `pytest tests/integration/test_dashboard_operator_readability.py`
   (copy roles, `YYYY-MM-DD HH:MM` clock, first-window no-scroll). This is
   also the CI Tests → Dashboard semantic release policy gate and the
   `check-dashboard-operator-readability` pre-push hook.

## Debug empty Run Explorer index

For **6. Run Explorer** panel `Inspect Recent Runs` (`id=3010`) or workflow
panel `3020`, do not start with Grafana selectors. `$pipeline` / `$run_type`
come from Prometheus and `$run_id` from the control-plane catalog; the table
reads `GET /ops/observability/pipeline-run-reports`.

1. From the checkout you are viewing, run
   `python scripts/ops/runtime/docker/verify_report_bind.py --pipeline chembl_assay`.
2. Confirm `GET /ops/observability/pipeline-run-reports?pipeline=chembl_assay&limit=3`
   `index_state`: `ok` (rows), `valid_empty` (no artifacts for that pipeline),
   or `tree_missing` / `layout_unhealthy` / `identity_unhealthy` (bind/origin).
3. `/health/ready` green is not proof the index should fill.
4. Do not start main from `/tmp/bioetl-issues*` without
   `--allow-transient-origin`. Recreate from the canonical checkout instead.

This single skill replaces `grafana-dashboard-extension`,
`grafana-dashboard-render`, `prometheus-metric-discovery`, and
`prometheus-query-debugger` for dashboard work.
