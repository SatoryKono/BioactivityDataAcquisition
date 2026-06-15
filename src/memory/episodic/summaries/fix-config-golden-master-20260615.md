---
id: fix-config-golden-master-20260615
title: Fix config golden master test failures
task_id: fix-config-golden-master-20260615
created_at: '2026-06-15T13:26:04Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Refreshed tests/snapshots/pipeline_configs.json via UPDATE_SNAPSHOTS=1 because
  PipelineConfig serialization now includes source_profile for all representative
  pipelines; Linux and Windows runs of tests/architecture/test_config_golden_master.py
  now pass without code changes.
---

# Episodic summary

## Task

- Title: Fix config golden master test failures

## Outcome

- Refreshed tests/snapshots/pipeline_configs.json via UPDATE_SNAPSHOTS=1 because PipelineConfig serialization now includes source_profile for all representative pipelines; Linux and Windows runs of tests/architecture/test_config_golden_master.py now pass without code changes.

## Lessons learned

- Replace with durable follow-up if needed
