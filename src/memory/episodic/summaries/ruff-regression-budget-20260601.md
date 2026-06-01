---
id: ruff-regression-budget-20260601
title: Fix ruff regression budget
task_id: ruff-regression-budget-20260601
created_at: '2026-06-01T07:48:48Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_regression_metrics.py
summary: Fixed the ruff regression budget by preserving _run_manifest_refs re-export
  aliases for data-root helpers, confirming all listed ruff violations are clean,
  and refreshing module coverage inventory source_tree_sha256 after src/bioetl changes.
---

# Episodic summary

## Task

- Title: Fix ruff regression budget

## Outcome

- Fixed the ruff regression budget by preserving _run_manifest_refs re-export aliases for data-root helpers, confirming all listed ruff violations are clean, and refreshing module coverage inventory source_tree_sha256 after src/bioetl changes.

## Lessons learned

- Replace with durable follow-up if needed
