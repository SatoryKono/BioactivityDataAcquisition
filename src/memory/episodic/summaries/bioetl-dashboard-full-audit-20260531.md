---
id: bioetl-dashboard-full-audit-20260531
title: Full BioETL dashboard audit
task_id: bioetl-dashboard-full-audit-20260531
created_at: '2026-05-31T16:57:31Z'
ttl_days: 14
confidence: episodic
source_refs:
- reports/observability/dashboard-audit-20260531/dashboard-audit-report.md
summary: Completed full BioETL dashboard audit for run b51986c6-870b-4457-aa70-baedac2710ad
  across seven shipped Grafana dashboards. Grafana, Prometheus, Loki, Tempo, and quarantine
  explorer were reachable; server-side Grafana rendering returned HTTP 500 and Playwright
  fallback is unavailable, so render status is documented as not_rendered with reason.
  Critical exact-run ID and Processed Records panels were live-audited after backend
  restart; Processed Records matches RunLedger metrics, but ID panel checkpoint anchor
  reports MISSING despite checkpoint history files existing. Audit artifacts include
  dashboard inventory, panel audit, findings, fix plan, and source-truth diff under
  reports/observability/dashboard-audit-20260531/.
---

# Episodic summary

## Task

- Title: Full BioETL dashboard audit

## Outcome

- Completed full BioETL dashboard audit for run b51986c6-870b-4457-aa70-baedac2710ad across seven shipped Grafana dashboards. Grafana, Prometheus, Loki, Tempo, and quarantine explorer were reachable; server-side Grafana rendering returned HTTP 500 and Playwright fallback is unavailable, so render status is documented as not_rendered with reason. Critical exact-run ID and Processed Records panels were live-audited after backend restart; Processed Records matches RunLedger metrics, but ID panel checkpoint anchor reports MISSING despite checkpoint history files existing. Audit artifacts include dashboard inventory, panel audit, findings, fix plan, and source-truth diff under reports/observability/dashboard-audit-20260531/.

## Lessons learned

- Replace with durable follow-up if needed
