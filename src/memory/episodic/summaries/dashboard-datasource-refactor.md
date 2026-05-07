---
id: dashboard-datasource-refactor
title: Implement dashboard datasource refactor
task_id: dashboard-datasource-refactor
created_at: '2026-05-07T12:11:34Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/integration/test_grafana_config.py
summary: Updated the datasource refactor plan, normalized shipped Prometheus panel
  and target datasource references to uid=prometheus across scoped dashboards, added
  an integration datasource contract test, synced grafana/README.md, and validated
  with JSON checks plus maintained narrow pytest slices.
---

# Episodic summary

## Task

- Title: Implement dashboard datasource refactor

## Outcome

- Updated the datasource refactor plan, normalized shipped Prometheus panel and target datasource references to uid=prometheus across scoped dashboards, added an integration datasource contract test, synced grafana/README.md, and validated with JSON checks plus maintained narrow pytest slices.

## Lessons learned

- Replace with durable follow-up if needed
