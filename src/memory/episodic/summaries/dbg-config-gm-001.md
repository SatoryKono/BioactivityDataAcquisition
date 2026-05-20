---
id: dbg-config-gm-001
title: Fix pipeline config golden master failures around alias_policy validation and
  snapshot drift
task_id: DBG-CONFIG-GM-001
created_at: '2026-05-20T06:39:39Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Verified current runtime no longer fails on alias_policy validation; golden
  master drift was caused by canonical data_schema now being included in serialized
  PipelineConfig. Refreshed tests/snapshots/pipeline_configs.json for all representative
  pipelines and updated stale unit assertions in tests/unit/infrastructure/config/test_pipeline_normalizers.py
  to expect projected data_schema payloads.
---

# Episodic summary

## Task

- Title: Fix pipeline config golden master failures around alias_policy validation and snapshot drift

## Outcome

- Verified current runtime no longer fails on alias_policy validation; golden master drift was caused by canonical data_schema now being included in serialized PipelineConfig. Refreshed tests/snapshots/pipeline_configs.json for all representative pipelines and updated stale unit assertions in tests/unit/infrastructure/config/test_pipeline_normalizers.py to expect projected data_schema payloads.

## Lessons learned

- Replace with durable follow-up if needed
