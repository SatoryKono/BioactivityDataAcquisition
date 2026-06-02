---
id: fix-cli-helper-timeout-20260602
title: Fix CLI helper timeout in test_run_with_valid_pipeline
task_id: fix-cli-helper-timeout-20260602
created_at: '2026-06-02T17:22:20Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Patched tests/unit/interfaces/cli/test_cli_helpers.py to stub publish_metrics_safely
  alongside detached observability backend startup, preventing CLI helper tests from
  entering heavy runtime provider/metrics registration during successful run command
  assertions. Verified ruff, the previously timing-out test, and the full test_cli_helpers
  module now pass.
---

# Episodic summary

## Task

- Title: Fix CLI helper timeout in test_run_with_valid_pipeline

## Outcome

- Patched tests/unit/interfaces/cli/test_cli_helpers.py to stub publish_metrics_safely alongside detached observability backend startup, preventing CLI helper tests from entering heavy runtime provider/metrics registration during successful run command assertions. Verified ruff, the previously timing-out test, and the full test_cli_helpers module now pass.

## Lessons learned

- Replace with durable follow-up if needed
