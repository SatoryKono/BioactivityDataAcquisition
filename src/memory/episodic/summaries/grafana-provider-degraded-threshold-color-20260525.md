---
id: grafana-provider-degraded-threshold-color-20260525
title: Fix provider degraded checks neutral threshold color
task_id: grafana-provider-degraded-threshold-color-20260525
created_at: '2026-05-25T06:01:08Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/dashboards/bioetl-provider-health-v2.json
- tests/integration/test_grafana_dashboard_metric_semantics.py
- tests/integration/test_grafana_config.py
summary: Changed the Provider Health dashboard panel 'Monitor Degraded Checks (Selected
  Range)' threshold color from blue to green so selected-range degraded count evidence
  remains neutral and matches integration semantic tests. Validated JSON, targeted
  semantic test, full dashboard metric semantics file, and Grafana config integration
  tests.
---

# Episodic summary

## Task

- Title: Fix provider degraded checks neutral threshold color

## Outcome

- Changed the Provider Health dashboard panel 'Monitor Degraded Checks (Selected Range)' threshold color from blue to green so selected-range degraded count evidence remains neutral and matches integration semantic tests. Validated JSON, targeted semantic test, full dashboard metric semantics file, and Grafana config integration tests.

## Lessons learned

- Replace with durable follow-up if needed
