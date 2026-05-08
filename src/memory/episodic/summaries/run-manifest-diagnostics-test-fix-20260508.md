---
id: run-manifest-diagnostics-test-fix-20260508
title: Fix run manifest diagnostics summary test
task_id: run-manifest-diagnostics-test-fix-20260508
created_at: '2026-05-08T07:24:23Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/application/services/test_run_manifest_diagnostics.py
summary: Updated the provenance-only run manifest diagnostics expected summary to
  include source_posture and input_snapshot_missing_source_refs, matching the current
  diagnostics contract already used by ledger-backed summaries.
---

# Episodic summary

## Task

- Title: Fix run manifest diagnostics summary test

## Outcome

- Updated the provenance-only run manifest diagnostics expected summary to include source_posture and input_snapshot_missing_source_refs, matching the current diagnostics contract already used by ledger-backed summaries.

## Lessons learned

- Replace with durable follow-up if needed
