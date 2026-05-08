---
id: fix-architecture-last-failed-20260508
title: Fix architecture last-failed regressions
task_id: fix-architecture-last-failed-20260508
created_at: '2026-05-08T11:16:47Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/providers/provider_registry.py
- src/bioetl/composition/providers/_registry_protocols.py
- tests/architecture/test_grafana_overview_v2_semantics.py
- configs/quality/integration_vcr_policy.yaml
- tests/integration/test_grafana_config.py
- tests/integration/test_grafana_layout_and_metadata.py
- tests/integration/test_grafana_dashboard_links.py
- tests/integration/test_grafana_dashboard_cta_links.py
summary: 'Fixed architecture last-failed regressions: synced dependency and scripts
  inventories, removed DataSourceRegistry freeze-guard leakage by renaming the internal
  provider protocol, kept provider registry facade below LOC cap, aligned overview
  semantics test with navigation panel links, updated VCR suite inventory, and split
  oversized Grafana integration test files.'
---

# Episodic summary

## Task

- Title: Fix architecture last-failed regressions

## Outcome

- Fixed architecture last-failed regressions: synced dependency and scripts inventories, removed DataSourceRegistry freeze-guard leakage by renaming the internal provider protocol, kept provider registry facade below LOC cap, aligned overview semantics test with navigation panel links, updated VCR suite inventory, and split oversized Grafana integration test files.

## Lessons learned

- Replace with durable follow-up if needed
