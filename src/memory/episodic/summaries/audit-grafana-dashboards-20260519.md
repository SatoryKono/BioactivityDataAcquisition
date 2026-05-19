---
id: audit-grafana-dashboards-20260519
title: Audit shipped Grafana dashboards and prepare improvement plan
task_id: audit-grafana-dashboards-20260519
created_at: '2026-05-19T04:08:38Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/dashboards
summary: 'Audited shipped Grafana dashboards against JSON SSOT and dashboard docs.
  Confirmed automated inventory parity and Grafana test pack pass. Main findings:
  control-plane navigation docs conflict with shipped omission of Explore adjunct
  links; runtime telemetry-gap first-screen panel is width=1 and under-visible; multiple
  docs remain stale on First Action/Next Action/Next Diagnostic Surface naming and
  workflow scope; dashboard-v2-updates.md is materially stale versus current JSON;
  selector docs still describe $workflow as multi-select although shipped dashboards
  are single-select with Include All or fail-closed single-select.'
---

# Episodic summary

## Task

- Title: Audit shipped Grafana dashboards and prepare improvement plan

## Outcome

- Audited shipped Grafana dashboards against JSON SSOT and dashboard docs. Confirmed automated inventory parity and Grafana test pack pass. Main findings: control-plane navigation docs conflict with shipped omission of Explore adjunct links; runtime telemetry-gap first-screen panel is width=1 and under-visible; multiple docs remain stale on First Action/Next Action/Next Diagnostic Surface naming and workflow scope; dashboard-v2-updates.md is materially stale versus current JSON; selector docs still describe $workflow as multi-select although shipped dashboards are single-select with Include All or fail-closed single-select.

## Lessons learned

- Replace with durable follow-up if needed
