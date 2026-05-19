---
id: benchmark-fixture-fix-20260518
title: Fix missing benchmark fixture in pytest suite
task_id: benchmark-fixture-fix-20260518
created_at: '2026-05-18T18:30:39Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/benchmarks/conftest.py
summary: Registered a fallback benchmark fixture plugin when pytest-benchmark is disabled
  so benchmark-marked suites skip cleanly instead of failing fixture resolution.
---

# Episodic summary

## Task

- Title: Fix missing benchmark fixture in pytest suite

## Outcome

- Registered a fallback benchmark fixture plugin when pytest-benchmark is disabled so benchmark-marked suites skip cleanly instead of failing fixture resolution.

## Lessons learned

- Replace with durable follow-up if needed
