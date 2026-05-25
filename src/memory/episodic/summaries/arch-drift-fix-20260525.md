---
id: arch-drift-fix-20260525
title: Fix architecture drift and bootstrap test failures
task_id: arch-drift-fix-20260525
created_at: '2026-05-25T10:47:02Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/scripts/test_normalization_governance_cli_smoke.py
summary: Also addressed a Windows timeout in normalization governance CLI smoke tests
  by removing duplicate heavy work inside the pipeline normalization matrix generator
  and giving the full execution smoke test an explicit 300s pytest budget with 180s
  subprocess limits.
---

# Episodic summary

## Task

- Title: Fix architecture drift and bootstrap test failures

## Outcome

- Also addressed a Windows timeout in normalization governance CLI smoke tests by removing duplicate heavy work inside the pipeline normalization matrix generator and giving the full execution smoke test an explicit 300s pytest budget with 180s subprocess limits.

## Lessons learned

- Replace with durable follow-up if needed
