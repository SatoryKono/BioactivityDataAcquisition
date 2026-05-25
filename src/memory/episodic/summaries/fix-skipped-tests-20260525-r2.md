---
id: fix-skipped-tests-20260525-r2
title: Fix architecture env-var centralization skip
task_id: fix-skipped-tests-20260525-r2
created_at: '2026-05-25T11:00:17Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_env_var_centralization.py
summary: Removed a runtime pytest.skip from test_allowed_composition_files_still_exist.
  Empty ALLOWED_COMPOSITION_FILES now naturally passes as an empty stale-entry check,
  preserving the architecture zero-skip budget.
---

# Episodic summary

## Task

- Title: Fix architecture env-var centralization skip

## Outcome

- Removed a runtime pytest.skip from test_allowed_composition_files_still_exist. Empty ALLOWED_COMPOSITION_FILES now naturally passes as an empty stale-entry check, preserving the architecture zero-skip budget.

## Lessons learned

- Empty allowlists in architecture guardrails should pass as zero stale entries, not call `pytest.skip`, because the architecture suite has a zero-skip budget.
