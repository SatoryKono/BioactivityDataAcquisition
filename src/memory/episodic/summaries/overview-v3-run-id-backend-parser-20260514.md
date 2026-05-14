---
id: overview-v3-run-id-backend-parser-20260514
title: Fix Overview v3 Run ID Infinity parser
task_id: overview-v3-run-id-backend-parser-20260514
created_at: '2026-05-14T08:05:25Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/dashboards/bioetl-overview-v3.json
summary: Added parser=backend to the Overview v3 run_id Infinity template variable
  so Grafana can populate the Run ID dropdown from /ops/control-plane/filter-options
  response_shape=list. Confirmed repo JSON and live Grafana API both expose parser=backend,
  and chembl_publication filter-options endpoint returns five run IDs for run_type
  All/backfill.
---

# Episodic summary

## Task

- Title: Fix Overview v3 Run ID Infinity parser

## Outcome

- Added parser=backend to the Overview v3 run_id Infinity template variable so Grafana can populate the Run ID dropdown from /ops/control-plane/filter-options response_shape=list. Confirmed repo JSON and live Grafana API both expose parser=backend, and chembl_publication filter-options endpoint returns five run IDs for run_type All/backfill.

## Lessons learned

- Replace with durable follow-up if needed
