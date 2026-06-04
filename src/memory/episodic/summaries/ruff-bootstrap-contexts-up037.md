---
id: ruff-bootstrap-contexts-up037
title: Fix bootstrap_contexts UP037 ruff regression
task_id: ruff-bootstrap-contexts-up037
created_at: '2026-06-04T12:19:06Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Fixed three UP037 ruff regressions in src/bioetl/composition/bootstrap_contexts.py
  by removing quotes from PipelineContext annotations under from __future__ import
  annotations. Refreshed module coverage inventory after src change. Validation passed
  for ruff on the file, test_regression_metrics.py::test_ruff_error_count, module
  coverage inventory --check, and module coverage source-tree hash guard.
---

# Episodic summary

## Task

- Title: Fix bootstrap_contexts UP037 ruff regression

## Outcome

- Fixed three UP037 ruff regressions in src/bioetl/composition/bootstrap_contexts.py by removing quotes from PipelineContext annotations under from __future__ import annotations. Refreshed module coverage inventory after src change. Validation passed for ruff on the file, test_regression_metrics.py::test_ruff_error_count, module coverage inventory --check, and module coverage source-tree hash guard.

## Lessons learned

- Replace with durable follow-up if needed
