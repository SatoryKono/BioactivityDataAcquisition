---
id: dashboard-selector-refactor-plan-20260515
title: Plan dashboard selector refactor
task_id: dashboard-selector-refactor-plan-20260515
created_at: '2026-05-15T04:45:22Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: 'Prepared source-first plan for Grafana selector refactor: current shipped
  dashboards use native Grafana variables with shared workflow/pipeline/run_type/run_id
  shell, run_id is HTTP-backed control-plane identity only, Workflow has status/step_status/step_kind;
  true reciprocal auto-selection and inactive/separate-row state filters require a
  control-plane selector catalog plus either hidden resolved vars or a custom selector
  panel/plugin because native Grafana JSON cannot write back other visible variable
  values or place variables on separate rows.'
---

# Episodic summary

## Task

- Title: Plan dashboard selector refactor

## Outcome

- Prepared source-first plan for Grafana selector refactor: current shipped dashboards use native Grafana variables with shared workflow/pipeline/run_type/run_id shell, run_id is HTTP-backed control-plane identity only, Workflow has status/step_status/step_kind; true reciprocal auto-selection and inactive/separate-row state filters require a control-plane selector catalog plus either hidden resolved vars or a custom selector panel/plugin because native Grafana JSON cannot write back other visible variable values or place variables on separate rows.

## Lessons learned

- Replace with durable follow-up if needed
