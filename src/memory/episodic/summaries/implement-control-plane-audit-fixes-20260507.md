---
id: implement-control-plane-audit-fixes-20260507
title: Implement Control Plane audit fixes
task_id: implement-control-plane-audit-fixes-20260507
created_at: '2026-05-07T14:39:36Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/memory/episodic/summaries/audit-control-plane-dashboard-20260507.md
summary: 'Implemented Control Plane dashboard fixes in grafana/dashboards/bioetl-control-plane-v1.json
  plus targeted tests/docs. Fixed panel 130 replay/resume blockers query to collapse
  empty selected-range series to 0 via per-component zero fallbacks; live Prometheus
  query now returns scalar 0 for chembl_activity/incremental case. Fixed panel 121
  conflicting runbook routing by aligning field-link with checkpoint-debugging path
  and clarifying description. Renamed audit panels 107-110 to GLOBAL variants and
  updated descriptions because their metric families are global and ignore pipeline/run_type.
  Added explicit run_type no-op disclosure to control-plane panels backed by metric
  families without run_type labels. Updated tests/integration/test_grafana_dashboard_metric_semantics.py,
  test_grafana_config.py, test_grafana_dashboard_links.py, and docs/03-guides/dashboards/panel-title-inventory.md.
  Checks passed: JSON validation, targeted control-plane config tests, control-plane
  link tests, targeted metric-semantics tests, dashboard inventory parity, visual
  semantics, and live Prometheus verification. Git status remained unavailable because
  local git-lfs filter-process is missing; validation relied on file scans and tests
  instead.'
---

# Episodic summary

## Task

- Title: Implement Control Plane audit fixes

## Outcome

- Implemented Control Plane dashboard fixes in grafana/dashboards/bioetl-control-plane-v1.json plus targeted tests/docs. Fixed panel 130 replay/resume blockers query to collapse empty selected-range series to 0 via per-component zero fallbacks; live Prometheus query now returns scalar 0 for chembl_activity/incremental case. Fixed panel 121 conflicting runbook routing by aligning field-link with checkpoint-debugging path and clarifying description. Renamed audit panels 107-110 to GLOBAL variants and updated descriptions because their metric families are global and ignore pipeline/run_type. Added explicit run_type no-op disclosure to control-plane panels backed by metric families without run_type labels. Updated tests/integration/test_grafana_dashboard_metric_semantics.py, test_grafana_config.py, test_grafana_dashboard_links.py, and docs/03-guides/dashboards/panel-title-inventory.md. Checks passed: JSON validation, targeted control-plane config tests, control-plane link tests, targeted metric-semantics tests, dashboard inventory parity, visual semantics, and live Prometheus verification. Git status remained unavailable because local git-lfs filter-process is missing; validation relied on file scans and tests instead.

## Lessons learned

- Replace with durable follow-up if needed
