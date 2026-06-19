---
id: fix-scorecard-hash-drift
title: Fix scorecard coverage evidence hash drift
task_id: fix-scorecard-hash-drift
created_at: '2026-06-19T19:21:46Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/domain/aggregates/_batch_mixins.py
summary: Also resolved the domain file-size regression by extracting shared Batch
  aggregate private attrs into src/bioetl/domain/aggregates/_batch_attrs.py, reducing
  _batch_mixins.py from 321 LOC to 290 LOC without changing behavior or debt limits;
  targeted code-metrics and aggregate-internal tests pass.
---

# Episodic summary

## Task

- Title: Fix scorecard coverage evidence hash drift

## Outcome

- Also resolved the domain file-size regression by extracting shared Batch aggregate private attrs into src/bioetl/domain/aggregates/_batch_attrs.py, reducing _batch_mixins.py from 321 LOC to 290 LOC without changing behavior or debt limits; targeted code-metrics and aggregate-internal tests pass.

## Lessons learned

- Replace with durable follow-up if needed
