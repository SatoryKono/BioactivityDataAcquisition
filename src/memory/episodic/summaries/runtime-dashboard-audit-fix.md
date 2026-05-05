---
id: runtime-dashboard-audit-fix
title: Fix Runtime dashboard audit findings
task_id: runtime-dashboard-audit-fix
created_at: '2026-05-05T17:08:44Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/dashboards/bioetl-runtime.json
summary: Updated Runtime dashboard no-data semantics for memory pressure, telemetry
  gap terminology, regression tests for UNKNOWN runtime telemetry, and Grafana README
  runtime answer-row docs. Targeted Grafana tests pass; dashboard visual semantics
  gate still has unrelated DQ/Overview/Provider failures.
---

# Episodic summary

## Task

- Title: Fix Runtime dashboard audit findings

## Outcome

- Updated Runtime dashboard no-data semantics for memory pressure, telemetry gap terminology, regression tests for UNKNOWN runtime telemetry, and Grafana README runtime answer-row docs. Targeted Grafana tests pass; dashboard visual semantics gate still has unrelated DQ/Overview/Provider failures.

## Lessons learned

- Replace with durable follow-up if needed
