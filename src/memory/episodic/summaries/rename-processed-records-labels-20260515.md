---
id: rename-processed-records-labels-20260515
title: Rename Processed Records display labels
task_id: rename-processed-records-labels-20260515
created_at: '2026-05-15T08:37:29Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/dashboards/bioetl-runtime.json
- tests/integration/test_grafana_dashboard_metric_semantics.py
summary: Renamed Processed Records parameter display labels across shipped Grafana
  dashboards while preserving raw sort keys and PromQL expressions; updated semantic
  regression tests; validated JSON, ruff, Grafana semantic/config tests, visual semantics,
  provisioning reload, and Grafana API labels.
---

# Episodic summary

## Task

- Title: Rename Processed Records display labels

## Outcome

- Renamed Processed Records parameter display labels across shipped Grafana dashboards while preserving raw sort keys and PromQL expressions; updated semantic regression tests; validated JSON, ruff, Grafana semantic/config tests, visual semantics, provisioning reload, and Grafana API labels.

## Lessons learned

- Replace with durable follow-up if needed
