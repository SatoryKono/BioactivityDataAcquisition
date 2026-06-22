---
id: pipeline-assembler-lazy-datasource-fix
title: Fix GenericPipelineFactory default data source creator regression
task_id: pipeline-assembler-lazy-datasource-fix
created_at: '2026-06-22T17:23:05Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/composition/factories/pipeline/test_assembler_unit.py
summary: Restored eager resolution of the default data-source creator in GenericPipelineFactory
  by routing constructor binding through the shared resolve_data_source_creator helper
  instead of a lazy closure.
---

# Episodic summary

## Task

- Title: Fix GenericPipelineFactory default data source creator regression

## Outcome

- Restored eager resolution of the default data-source creator in GenericPipelineFactory by routing constructor binding through the shared resolve_data_source_creator helper instead of a lazy closure.

## Lessons learned

- Replace with durable follow-up if needed
