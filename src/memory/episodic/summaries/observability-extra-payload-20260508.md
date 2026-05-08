---
id: observability-extra-payload-20260508
title: Fix nested LoggerPort extra payloads
task_id: observability-extra-payload-20260508
created_at: '2026-05-08T10:34:10Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/execution_api.py
- src/bioetl/composition/_pipeline_execution.py
- src/bioetl/interfaces/observability.py
- tests/unit/composition/test_observability_contract.py
summary: Removed literal extra= keyword callsites from composition metrics gateway
  wrappers while preserving grouping_key_extra compatibility via kwargs; omitted None
  grouping key payloads in interfaces observability wrapper.
---

# Episodic summary

## Task

- Title: Fix nested LoggerPort extra payloads

## Outcome

- Removed literal extra= keyword callsites from composition metrics gateway wrappers while preserving grouping_key_extra compatibility via kwargs; omitted None grouping key payloads in interfaces observability wrapper.

## Lessons learned

- Replace with durable follow-up if needed
