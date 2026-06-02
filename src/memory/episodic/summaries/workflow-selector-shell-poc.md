---
id: workflow-selector-shell-poc
title: Implement visible exact-run selector shell
task_id: workflow-selector-shell-poc
created_at: '2026-06-02T05:12:27Z'
ttl_days: 14
confidence: episodic
source_refs:
- grafana/plugins/bioetl-selectorshell-panel/src/components/SimplePanel.tsx
- grafana/plugins/bioetl-selectorshell-panel/src/sync.ts
- docs/03-guides/dashboards/contracts/selector-contracts.yaml
- tests/integration/test_grafana_config.py
summary: Added a local Grafana panel plugin scaffold under grafana/plugins/bioetl-selectorshell-panel
  that resolves workflow/pipeline/run_type from exact run_id via /ops/control-plane/selector-context
  and can write visible selector vars back through locationService.partial(). Documented
  it as an optional unsigned local pilot and added a dashboard-config guard so shipped
  dashboards do not depend on the plugin yet.
---

# Episodic summary

## Task

- Title: Implement visible exact-run selector shell

## Outcome

- Added a local Grafana panel plugin scaffold under grafana/plugins/bioetl-selectorshell-panel that resolves workflow/pipeline/run_type from exact run_id via /ops/control-plane/selector-context and can write visible selector vars back through locationService.partial(). Documented it as an optional unsigned local pilot and added a dashboard-config guard so shipped dashboards do not depend on the plugin yet.

## Lessons learned

- Replace with durable follow-up if needed
