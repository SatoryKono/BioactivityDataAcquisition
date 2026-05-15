---
id: fix-processed-records-panel-order-20260515
title: Fix Processed Records panel row ordering
task_id: fix-processed-records-panel-order-20260515
created_at: '2026-05-15T07:40:13Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/dashboards/bioetl-runtime.json
- tests/integration/test_grafana_dashboard_metric_semantics.py
summary: Fixed Processed Records table display by using zero-padded parameter sort
  keys and clean value mappings across shipped Grafana dashboards; added regression
  coverage for row sorting and display labels; validated JSON, Grafana semantic tests,
  config tests, visual semantics, live Prometheus query, and Grafana API provisioning.
---

# Episodic summary

## Task

- Title: Fix Processed Records panel row ordering

## Outcome

- Fixed Processed Records table display by using zero-padded parameter sort keys and clean value mappings across shipped Grafana dashboards; added regression coverage for row sorting and display labels; validated JSON, Grafana semantic tests, config tests, visual semantics, live Prometheus query, and Grafana API provisioning.

## Lessons learned

- Replace with durable follow-up if needed
