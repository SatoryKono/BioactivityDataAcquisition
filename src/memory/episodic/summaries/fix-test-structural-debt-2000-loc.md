---
id: fix-test-structural-debt-2000-loc
title: Fix test structural debt guardrails
task_id: fix-test-structural-debt-2000-loc
created_at: '2026-06-16T08:08:25Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_test_structural_debt.py
summary: Resolved reported test structural debt guardrails by keeping health-server
  control-plane identity tests below the 2000 LOC cap with checkpoint freshness coverage
  in its focused module, and by splitting the workflow services coverage test into
  separate runner-service and execution-service paths so no test function exceeds
  200 LOC. Validated with ruff, targeted unit tests, and the structural debt architecture
  tests.
---

# Episodic summary

## Task

- Title: Fix test structural debt guardrails

## Outcome

- Resolved reported test structural debt guardrails by keeping health-server control-plane identity tests below the 2000 LOC cap with checkpoint freshness coverage in its focused module, and by splitting the workflow services coverage test into separate runner-service and execution-service paths so no test function exceeds 200 LOC. Validated with ruff, targeted unit tests, and the structural debt architecture tests.

## Lessons learned

- Replace with durable follow-up if needed
