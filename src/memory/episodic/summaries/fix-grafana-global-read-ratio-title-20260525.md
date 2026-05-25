---
id: fix-grafana-global-read-ratio-title-20260525
title: Fix Grafana global read failure ratio title
task_id: fix-grafana-global-read-ratio-title-20260525
created_at: '2026-05-25T10:22:57Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/dashboards/bioetl-control-plane-v1.json
summary: 'Renamed bioetl-control-plane-v1 panel id 136 from Monitor: GLOBAL Control-Plane
  Read Failure Ratio to Monitor: GLOBAL Control-Plane Read Failure Ratio Severity
  so integration tests and shipped docs agree on the global severity panel title.'
---

# Episodic summary

## Task

- Title: Fix Grafana global read failure ratio title

## Outcome

- Renamed bioetl-control-plane-v1 panel id 136 from Monitor: GLOBAL Control-Plane Read Failure Ratio to Monitor: GLOBAL Control-Plane Read Failure Ratio Severity so integration tests and shipped docs agree on the global severity panel title.

## Lessons learned

- Dashboard title inventory and integration tests can already encode the intended operator wording; when only shipped JSON drifts, prefer a localized JSON title fix over changing tests.
