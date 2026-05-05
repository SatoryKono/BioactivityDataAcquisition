---
id: runtime-dashboard-audit-fix
title: Fix Runtime dashboard audit findings
task_id: runtime-dashboard-audit-fix
created_at: '2026-05-05T17:10:32Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/dashboards/bioetl-runtime.json
summary: Fixed Runtime dashboard no-data semantics by preserving UNKNOWN for runtime
  diagnostic panels, added regression coverage for telemetry gap/no-data behavior
  and infrastructure blocker detail, updated Grafana README. Targeted Grafana tests
  passed; visual semantics gate still fails only on out-of-scope DQ/Overview/Provider
  dashboard debt.
---

# Episodic summary

## Task

- Title: Fix Runtime dashboard audit findings

## Outcome

- Fixed Runtime dashboard no-data semantics by preserving UNKNOWN for runtime diagnostic panels, added regression coverage for telemetry gap/no-data behavior and infrastructure blocker detail, updated Grafana README. Targeted Grafana tests passed; visual semantics gate still fails only on out-of-scope DQ/Overview/Provider dashboard debt.

## Lessons learned

- Replace with durable follow-up if needed
