---
id: fix-delta-schema-cli-register
title: Fix Delta schema and CLI register seam test failures
task_id: FIX-DELTA-SCHEMA-CLI-REGISTER
created_at: '2026-06-18T14:52:21Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/infrastructure/storage/delta/schema_ops.py;src/bioetl/interfaces/cli/main.py
summary: 'Validated reported AttributeError classes. Current checkout routes Delta
  schema conversion through delta_schema_to_pyarrow(), which prefers to_arrow() and
  falls back to to_pyarrow(), and bioetl.interfaces.cli.main exposes register_all_pipelines
  for legacy CLI test patching. Retests passed: Silver/storage integration subset
  24/24, pipeline/workflow subset 8/8, CLI run_all_command 31/31 with Silver default
  merge, CLI helpers 30/30. No new source edits were required in this turn.'
---

# Episodic summary

## Task

- Title: Fix Delta schema and CLI register seam test failures

## Outcome

- Validated reported AttributeError classes. Current checkout routes Delta schema conversion through delta_schema_to_pyarrow(), which prefers to_arrow() and falls back to to_pyarrow(), and bioetl.interfaces.cli.main exposes register_all_pipelines for legacy CLI test patching. Retests passed: Silver/storage integration subset 24/24, pipeline/workflow subset 8/8, CLI run_all_command 31/31 with Silver default merge, CLI helpers 30/30. No new source edits were required in this turn.

## Lessons learned

- Replace with durable follow-up if needed
