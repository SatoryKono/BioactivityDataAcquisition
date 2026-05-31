---
id: grafana-grid-overlap-fix
title: Fix Grafana dashboard grid overlap
task_id: grafana-grid-overlap-fix
created_at: '2026-05-31T17:50:26Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/integration/test_grafana_dashboard_first_screen_contract.py
summary: Moved the collapsed top-level Alert/SLO Triage row in bioetl-overview-v2
  below the existing historical and diagnostics rows to eliminate root grid overlap
  with L1 Historical Trends while preserving panel IDs, queries, and operator flow.
  JSON validation and targeted first-screen layout tests passed.
---

# Episodic summary

## Task

- Title: Fix Grafana dashboard grid overlap

## Outcome

- Moved the collapsed top-level Alert/SLO Triage row in bioetl-overview-v2 below the existing historical and diagnostics rows to eliminate root grid overlap with L1 Historical Trends while preserving panel IDs, queries, and operator flow. JSON validation and targeted first-screen layout tests passed.

## Lessons learned

- Replace with durable follow-up if needed
