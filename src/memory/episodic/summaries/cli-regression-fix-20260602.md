---
id: cli-regression-fix-20260602
title: Fix CLI command regression tests
task_id: cli-regression-fix-20260602
created_at: '2026-06-02T11:00:10Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Restored CLI patch seams and test-time registry behavior after compatibility
  refactor. workflow.py now calls runtime helpers through the _workflow_command_runtime
  module seam so unit tests patch the exact execution path. domains/run/support.py
  no longer reuses the shared default registry marker as a populated fallback, which
  restores fallback registry caching on Click context while preserving the explicit
  populated-registry patch seam. Verified with targeted and adjacent CLI pytest batches
  plus ruff on touched files.
---

# Episodic summary

## Task

- Title: Fix CLI command regression tests

## Outcome

- Restored CLI patch seams and test-time registry behavior after compatibility refactor. workflow.py now calls runtime helpers through the _workflow_command_runtime module seam so unit tests patch the exact execution path. domains/run/support.py no longer reuses the shared default registry marker as a populated fallback, which restores fallback registry caching on Click context while preserving the explicit populated-registry patch seam. Verified with targeted and adjacent CLI pytest batches plus ruff on touched files.

## Lessons learned

- Replace with durable follow-up if needed
