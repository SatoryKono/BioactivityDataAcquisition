---
id: grafana-dashboard-error-fixes-20260601
title: Fix BioETL dashboard render and live-audit tooling errors
task_id: grafana-dashboard-error-fixes-20260601
created_at: '2026-06-01T19:24:50Z'
ttl_days: 14
confidence: episodic
source_refs:
- scripts/ops/observability/grafana/rerender_grafana_screenshots.py
summary: 'Implemented dashboard audit tooling fixes: Playwright runtime and fallback
  now have hard timeouts; Grafana rerender writes render-manifest.json with per-dashboard
  render_results even on partial Render API failure; live-audit required reviewed
  specs are rebound to concrete discovered target refIds to avoid duplicate target_ref_id=None
  failures. Validation passed for unit dashboard tooling tests, dashboard link/selector
  integration tests, ruff check, non-hanging preflight JSON, and full scoped Render
  API rerender of all 8 dashboards.'
---

# Episodic summary

## Task

- Title: Fix BioETL dashboard render and live-audit tooling errors

## Outcome

- Implemented dashboard audit tooling fixes: Playwright runtime and fallback now have hard timeouts; Grafana rerender writes render-manifest.json with per-dashboard render_results even on partial Render API failure; live-audit required reviewed specs are rebound to concrete discovered target refIds to avoid duplicate target_ref_id=None failures. Validation passed for unit dashboard tooling tests, dashboard link/selector integration tests, ruff check, non-hanging preflight JSON, and full scoped Render API rerender of all 8 dashboards.

## Lessons learned

- Replace with durable follow-up if needed
