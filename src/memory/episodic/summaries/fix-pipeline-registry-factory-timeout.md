---
id: fix-pipeline-registry-factory-timeout
title: Fix pipeline registry factory timeout in pipeline factory tests
task_id: fix_pipeline_registry_factory_timeout
created_at: '2026-06-15T17:26:17Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Made get_data_source_creator return a lazy cached provider-bound creator
  so pipeline registry factory exports no longer trigger full provider loading during
  factory construction. Preserved eager failure for unknown providers when the registry
  is already loaded. Refreshed module coverage inventory and architecture scorecard
  artifacts; verified pipeline factory, generic factory, and assembler unit tests
  on Linux and Windows.
---

# Episodic summary

## Task

- Title: Fix pipeline registry factory timeout in pipeline factory tests

## Outcome

- Made get_data_source_creator return a lazy cached provider-bound creator so pipeline registry factory exports no longer trigger full provider loading during factory construction. Preserved eager failure for unknown providers when the registry is already loaded. Refreshed module coverage inventory and architecture scorecard artifacts; verified pipeline factory, generic factory, and assembler unit tests on Linux and Windows.

## Lessons learned

- Replace with durable follow-up if needed
