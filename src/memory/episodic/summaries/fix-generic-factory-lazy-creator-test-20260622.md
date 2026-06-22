---
id: fix-generic-factory-lazy-creator-test-20260622
title: Fix GenericPipelineFactory lazy data source creator tests
task_id: fix-generic-factory-lazy-creator-test-20260622
created_at: '2026-06-22T17:27:24Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/composition/test_generic_factory.py
summary: 'Investigated reported failures in tests/unit/composition/test_generic_factory.py
  where get_data_source_creator was expected once but called zero times. Current working
  tree does not reproduce: GenericPipelineFactory resolves the public assembler get_data_source_creator
  seam during __init__, and targeted tests pass in both WSL .venv and Windows .venv-win.
  No source change was needed for this reported failure; likely stale test run state
  before current _assembler_factory/import-surface changes.'
---

# Episodic summary

## Task

- Title: Fix GenericPipelineFactory lazy data source creator tests

## Outcome

- Investigated reported failures in tests/unit/composition/test_generic_factory.py where get_data_source_creator was expected once but called zero times. Current working tree does not reproduce: GenericPipelineFactory resolves the public assembler get_data_source_creator seam during __init__, and targeted tests pass in both WSL .venv and Windows .venv-win. No source change was needed for this reported failure; likely stale test run state before current _assembler_factory/import-surface changes.

## Lessons learned

- Replace with durable follow-up if needed
