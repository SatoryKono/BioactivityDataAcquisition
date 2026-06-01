---
id: dashboard-visible-nav-handoff-fix-20260601
title: Fix visible Grafana navigation bus variable handoff
task_id: dashboard-visible-nav-handoff-fix-20260601
created_at: '2026-06-01T18:49:03Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/integration/test_grafana_dashboard_links.py
summary: Fixed visible HTML navigation bus handoffs in primary Grafana dashboards
  by synchronizing panel id=1000 HTML hrefs with canonical panel.links. Added regression
  tests to require workflow/pipeline/run_type/run_id preservation for primary dashboard
  HTML anchors and to keep Silver Reject Explorer forensic boundary. Updated dashboard
  extension docs. Validated JSON, ruff, local handoff scan, and targeted dashboard
  link/selector/runtime tests.
---

# Episodic summary

## Task

- Title: Fix visible Grafana navigation bus variable handoff

## Outcome

- Fixed visible HTML navigation bus handoffs in primary Grafana dashboards by synchronizing panel id=1000 HTML hrefs with canonical panel.links. Added regression tests to require workflow/pipeline/run_type/run_id preservation for primary dashboard HTML anchors and to keep Silver Reject Explorer forensic boundary. Updated dashboard extension docs. Validated JSON, ruff, local handoff scan, and targeted dashboard link/selector/runtime tests.

## Lessons learned

- Replace with durable follow-up if needed
