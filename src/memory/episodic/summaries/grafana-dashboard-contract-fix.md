---
id: grafana-dashboard-contract-fix
title: Fix Grafana dashboard first-screen contract failures
task_id: grafana-dashboard-contract-fix
created_at: '2026-06-01T16:28:38Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/dashboards/bioetl-workflow-overview.json
summary: Adjusted workflow shared-shell layout to restore the common Status panel
  width, relocated workflow-specific Pipeline Status out of the shared header row,
  and added explicit UNKNOWN noValue handling to the control-plane telemetry trust
  marker. Targeted Grafana dashboard contract tests passed.
---

# Episodic summary

## Task

- Title: Fix Grafana dashboard first-screen contract failures

## Outcome

- Adjusted workflow shared-shell layout to restore the common Status panel width, relocated workflow-specific Pipeline Status out of the shared header row, and added explicit UNKNOWN noValue handling to the control-plane telemetry trust marker. Targeted Grafana dashboard contract tests passed.

## Lessons learned

- Replace with durable follow-up if needed
