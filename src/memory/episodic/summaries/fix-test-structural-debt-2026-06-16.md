---
id: fix-test-structural-debt-2026-06-16
title: Fix oversized quality integral gate test
task_id: fix-test-structural-debt-2026-06-16
created_at: '2026-06-16T12:46:18Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/scripts/ci/test_quality_integral_gate.py
summary: Split the oversized debt-governance quality gate test into shared module-level
  fakes/helpers plus two shorter assertions-focused tests. Verified the updated unit
  module and the structural-debt architecture guardrail both pass.
---

# Episodic summary

## Task

- Title: Fix oversized quality integral gate test

## Outcome

- Split the oversized debt-governance quality gate test into shared module-level fakes/helpers plus two shorter assertions-focused tests. Verified the updated unit module and the structural-debt architecture guardrail both pass.

## Lessons learned

- Replace with durable follow-up if needed
