---
id: ruff-regression-metrics-fix
title: Fix ruff regression metrics
task_id: ruff-regression-metrics-fix
created_at: '2026-05-06T10:19:20Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_regression_metrics.py
summary: Fixed ruff regression budget violations by sorting __all__ exports/imports
  and documenting the deprecated RunExecutionContext lazy compatibility export. Verified
  targeted ruff check, diff whitespace check, and test_regression_metrics.py::test_ruff_error_count
  pass.
---

# Episodic summary

## Task

- Title: Fix ruff regression metrics

## Outcome

- Fixed ruff regression budget violations by sorting __all__ exports/imports and documenting the deprecated RunExecutionContext lazy compatibility export. Verified targeted ruff check, diff whitespace check, and test_regression_metrics.py::test_ruff_error_count pass.

## Lessons learned

- Replace with durable follow-up if needed
