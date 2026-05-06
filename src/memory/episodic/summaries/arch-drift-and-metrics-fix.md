---
id: arch-drift-and-metrics-fix
title: Fix architecture drift and metrics regressions
task_id: arch-drift-and-metrics-fix
created_at: '2026-05-06T14:13:03Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_code_metrics.py
summary: Split replay-readiness verdict helpers into a private domain module, decomposed
  manifest creation support to keep function length under the architecture threshold,
  regenerated module dependency map artifacts, and verified the previously failing
  architecture checks.
---

# Episodic summary

## Task

- Title: Fix architecture drift and metrics regressions

## Outcome

- Split replay-readiness verdict helpers into a private domain module, decomposed manifest creation support to keep function length under the architecture threshold, regenerated module dependency map artifacts, and verified the previously failing architecture checks.

## Lessons learned

- Replace with durable follow-up if needed
