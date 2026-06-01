---
id: workflow-dashboard-verdict-fix
title: Fix workflow overview fail-closed pipeline status verdict contract
task_id: workflow-dashboard-verdict-fix
created_at: '2026-06-01T17:10:53Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/dashboards/bioetl-workflow-overview.json
summary: Renamed workflow overview panel id=9404 from Range Pipeline Status back to
  Pipeline Status to match the fail-closed current-verdict contract, and synchronized
  the single integration test that still expected the stale title.
---

# Episodic summary

## Task

- Title: Fix workflow overview fail-closed pipeline status verdict contract

## Outcome

- Renamed workflow overview panel id=9404 from Range Pipeline Status back to Pipeline Status to match the fail-closed current-verdict contract, and synchronized the single integration test that still expected the stale title.

## Lessons learned

- Replace with durable follow-up if needed
