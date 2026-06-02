---
id: grafana-full-audit-current-20260601
title: Full current BioETL Grafana dashboard audit
task_id: grafana-full-audit-current-20260601
created_at: '2026-06-01T19:10:52Z'
ttl_days: 14
confidence: episodic
source_refs:
- reports/observability/grafana/dashboard_audit_20260601_after_nav_fix/live-panel-audit.json
summary: Ran current BioETL Grafana dashboard audit. Inventory found 8 dashboards
  and 223 static panel rows. Collapsed rows are expanded. Grafana/Prometheus reachable,
  Quarantine Explorer backend on :8081 unavailable for direct source-of-truth checks.
  Server-side render produced 7 PNGs; bioetl-workflow-overview failed Grafana Render
  API with HTTP 500 and browser fallback hung on goto. Live panel audit produced 225
  results with 221 ok and 4 error/blocked_unavailable entries tied to unavailable
  HTTP-backed source checks. Targeted dashboard link/selector/collapsed/no-data/description
  tests passed.
---

# Episodic summary

## Task

- Title: Full current BioETL Grafana dashboard audit

## Outcome

- Ran current BioETL Grafana dashboard audit. Inventory found 8 dashboards and 223 static panel rows. Collapsed rows are expanded. Grafana/Prometheus reachable, Quarantine Explorer backend on :8081 unavailable for direct source-of-truth checks. Server-side render produced 7 PNGs; bioetl-workflow-overview failed Grafana Render API with HTTP 500 and browser fallback hung on goto. Live panel audit produced 225 results with 221 ok and 4 error/blocked_unavailable entries tied to unavailable HTTP-backed source checks. Targeted dashboard link/selector/collapsed/no-data/description tests passed.

## Lessons learned

- Replace with durable follow-up if needed
