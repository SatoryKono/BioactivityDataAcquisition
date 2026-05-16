---
id: selector-contract-audit-20260516
title: Audit Grafana selector contract drift
task_id: selector-contract-audit-20260516
created_at: '2026-05-16T08:00:36Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/dashboards
summary: Audited shipped grafana/dashboards selector variables and dashboard-to-dashboard
  links. Confirmed time range is preserved, no unknown target var names, but shared
  selector values are not consistently propagated because links omit workflow/pipeline/run_type
  in several target families and Provider/Workflow rely on hidden context aliases.
  No dashboard JSON changes were made.
---

# Episodic summary

## Task

- Title: Audit Grafana selector contract drift

## Outcome

- Audited shipped grafana/dashboards selector variables and dashboard-to-dashboard links. Confirmed time range is preserved, no unknown target var names, but shared selector values are not consistently propagated because links omit workflow/pipeline/run_type in several target families and Provider/Workflow rely on hidden context aliases. No dashboard JSON changes were made.

## Lessons learned

- Replace with durable follow-up if needed
