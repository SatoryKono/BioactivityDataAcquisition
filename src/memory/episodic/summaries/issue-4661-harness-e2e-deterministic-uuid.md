---
id: issue-4661-harness-e2e-deterministic-uuid
title: Replace nondeterministic UUID generation in harness-mode E2E tests
task_id: issue-4661-harness-e2e-deterministic-uuid
created_at: '2026-05-26T05:37:32Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/e2e/test_advanced_scenarios_e2e.py
summary: Replaced advanced harness-mode E2E context creation with callsite-seeded
  deterministic build_e2e_run_context usage, added architecture guard against create_test_context/uuid4
  regression on advanced harness targets, and validated ruff, deterministic guard,
  selected advanced E2E run_id regression, and governance uuid4_call_sites budget.
---

# Episodic summary

## Task

- Title: Replace nondeterministic UUID generation in harness-mode E2E tests

## Outcome

- Replaced advanced harness-mode E2E context creation with callsite-seeded deterministic build_e2e_run_context usage, added architecture guard against create_test_context/uuid4 regression on advanced harness targets, and validated ruff, deterministic guard, selected advanced E2E run_id regression, and governance uuid4_call_sites budget.

## Lessons learned

- Replace with durable follow-up if needed
