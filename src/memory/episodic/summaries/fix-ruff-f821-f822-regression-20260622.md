---
id: fix-ruff-f821-f822-regression-20260622
title: Fix ruff F821/F822 regression metrics
task_id: fix-ruff-f821-f822-regression-20260622
created_at: '2026-06-22T17:43:26Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_regression_metrics.py
summary: 'Resolved ruff regression metrics report: current source now defines CompositeRuntimeStorageProtocol
  for TYPE_CHECKING cast, imports JsonDict in contract_policy_loader, and statically
  binds composite command wrapper exports so F821/F822 count is zero. Validation passed:
  ruff on affected files, tests/architecture/test_regression_metrics.py::test_ruff_error_count,
  CLI wrapper contract tests, architecture scorecard guard; module coverage source
  hash guard skipped on WSL. Refreshed architecture scorecard source hash evidence.'
---

# Episodic summary

## Task

- Title: Fix ruff F821/F822 regression metrics

## Outcome

- Resolved ruff regression metrics report: current source now defines CompositeRuntimeStorageProtocol for TYPE_CHECKING cast, imports JsonDict in contract_policy_loader, and statically binds composite command wrapper exports so F821/F822 count is zero. Validation passed: ruff on affected files, tests/architecture/test_regression_metrics.py::test_ruff_error_count, CLI wrapper contract tests, architecture scorecard guard; module coverage source hash guard skipped on WSL. Refreshed architecture scorecard source hash evidence.

## Lessons learned

- Replace with durable follow-up if needed
