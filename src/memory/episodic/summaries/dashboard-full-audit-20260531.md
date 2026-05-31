---
id: dashboard-full-audit-20260531
title: Full BioETL dashboard audit
task_id: dashboard-full-audit-20260531
created_at: '2026-05-31T14:34:51Z'
ttl_days: 14
confidence: episodic
source_refs:
- reports/codex/dashboard-audit-20260531/AUDIT_REPORT_RU.md
summary: Audited all seven shipped Grafana dashboards for chembl_target/backfill run
  b51986c6-870b-4457-aa70-baedac2710ad. Render was blocked by Grafana render API 500
  and Playwright Chromium shared-library/sudo blocker. Generated panel-by-panel audit
  artifacts, checked 135 Prometheus queries, ran live HTTP panel audit, and confirmed
  P1 findings CP-ID-001 checkpoint identity drift, PR-GOLD-001 processed-records gold
  semantics drift, and AUTO-002 Provider Health Status invalid PromQL.
---

# Episodic summary

## Task

- Title: Full BioETL dashboard audit

## Outcome

- Audited all seven shipped Grafana dashboards for chembl_target/backfill run b51986c6-870b-4457-aa70-baedac2710ad. Render was blocked by Grafana render API 500 and Playwright Chromium shared-library/sudo blocker. Generated panel-by-panel audit artifacts, checked 135 Prometheus queries, ran live HTTP panel audit, and confirmed P1 findings CP-ID-001 checkpoint identity drift, PR-GOLD-001 processed-records gold semantics drift, and AUTO-002 Provider Health Status invalid PromQL.

## Lessons learned

- Replace with durable follow-up if needed
