---
id: provider-health-scroll-fix
title: Fix Provider Health table scroll and raw metric columns
task_id: provider-health-scroll-fix
created_at: '2026-05-11T13:58:36Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/dashboards/bioetl-provider-health-v2.json
summary: Removed raw Prometheus table columns from Provider Health first-screen tables
  by organizing visible fields for current status and top causes, while preserving
  the existing provider variable contract that still uses a __name__ metric-name union.
---

# Episodic summary

## Task

- Title: Fix Provider Health table scroll and raw metric columns

## Outcome

- Removed raw Prometheus table columns from Provider Health first-screen tables by organizing visible fields for current status and top causes, while preserving the existing provider variable contract that still uses a __name__ metric-name union.

## Lessons learned

- Replace with durable follow-up if needed
