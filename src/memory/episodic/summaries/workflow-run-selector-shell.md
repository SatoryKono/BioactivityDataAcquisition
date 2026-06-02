---
id: workflow-run-selector-shell
title: Implement exact-run hidden selector handoff
task_id: workflow-run-selector-shell
created_at: '2026-06-01T19:39:47Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/interfaces/http/_health_server_routing_support.py
- grafana/dashboards/bioetl-workflow-overview.json
- docs/03-guides/dashboards/contracts/selector-contracts.yaml
summary: Added exact_run_only/fallback support to control-plane filter-options, extended
  workflow dashboard with hidden workflow_context/pipeline_context_exact/run_type_context_exact/provider_context_exact
  vars, and rewired workflow handoffs to preserve exact run identity without auto-writing
  visible selectors.
---

# Episodic summary

## Task

- Title: Implement exact-run hidden selector handoff

## Outcome

- Added exact_run_only/fallback support to control-plane filter-options, extended workflow dashboard with hidden workflow_context/pipeline_context_exact/run_type_context_exact/provider_context_exact vars, and rewired workflow handoffs to preserve exact run identity without auto-writing visible selectors.

## Lessons learned

- Replace with durable follow-up if needed
