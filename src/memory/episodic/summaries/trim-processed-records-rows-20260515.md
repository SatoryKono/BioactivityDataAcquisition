---
id: trim-processed-records-rows-20260515
title: Trim Processed Records panel rows
task_id: trim-processed-records-rows-20260515
created_at: '2026-05-15T08:18:38Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/dashboards/bioetl-runtime.json
- tests/integration/test_grafana_dashboard_metric_semantics.py
- docs/03-guides/dashboards/design-system.md
summary: Removed Processed Records table rows for reconciliation_status, silver_accounted_records,
  silver_delta_vs_bronze, gold_accounted_records, and gold_delta_vs_valid_silver across
  shipped Grafana dashboards; updated semantic regression tests and dashboard docs;
  validated JSON, Grafana semantic/config tests, visual semantics, live Prometheus
  query, and Grafana provisioning reload.
---

# Episodic summary

## Task

- Title: Trim Processed Records panel rows

## Outcome

- Removed Processed Records table rows for reconciliation_status, silver_accounted_records, silver_delta_vs_bronze, gold_accounted_records, and gold_delta_vs_valid_silver across shipped Grafana dashboards; updated semantic regression tests and dashboard docs; validated JSON, Grafana semantic/config tests, visual semantics, live Prometheus query, and Grafana provisioning reload.

## Lessons learned

- Replace with durable follow-up if needed
