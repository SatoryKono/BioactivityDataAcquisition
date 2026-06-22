---
id: ruff-composite-import-sorting-20260622
title: Fix composite ruff import ordering regressions
task_id: ruff-composite-import-sorting-20260622
created_at: '2026-06-22T12:51:56Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/domain/composite/__init__.py
summary: Fixed reported ruff_error_count regressions by applying ruff import and __all__
  sorting to composite preflight validator, domain composite facade, and composite
  config base schema. Verified targeted ruff and tests/architecture/test_regression_metrics.py::test_ruff_error_count
  pass. Refreshed module coverage inventory after src changes; source-tree hash guard
  is skipped by repo policy on WSL.
---

# Episodic summary

## Task

- Title: Fix composite ruff import ordering regressions

## Outcome

- Fixed reported ruff_error_count regressions by applying ruff import and __all__ sorting to composite preflight validator, domain composite facade, and composite config base schema. Verified targeted ruff and tests/architecture/test_regression_metrics.py::test_ruff_error_count pass. Refreshed module coverage inventory after src changes; source-tree hash guard is skipped by repo policy on WSL.

## Lessons learned

- Replace with durable follow-up if needed
