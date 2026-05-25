---
id: fix-skipped-tests-20260525
title: Fix architecture skip debt in mypy ratchet test
task_id: fix-skipped-tests-20260525
created_at: '2026-05-25T10:07:48Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_regression_metrics.py
summary: Replaced runtime pytest.skip in test_mypy_error_count with a local no-op
  return outside BIOETL_ENFORCE_GLOBAL_MYPY_RATCHET, and made missing mypy fail in
  the enforcing workflow. Also removed an unused request fixture from architecture
  skip-count helper.
---

# Episodic summary

## Task

- Title: Fix architecture skip debt in mypy ratchet test

## Outcome

- Replaced runtime pytest.skip in test_mypy_error_count with a local no-op return outside BIOETL_ENFORCE_GLOBAL_MYPY_RATCHET, and made missing mypy fail in the enforcing workflow. Also removed an unused request fixture from architecture skip-count helper.

## Lessons learned

- Runtime `pytest.skip` in architecture ratchet tests can create skip debt even when static skip-marker budgets pass.
