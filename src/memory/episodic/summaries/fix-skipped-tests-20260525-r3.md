---
id: fix-skipped-tests-20260525-r3
title: Audit remaining skipped tests
task_id: fix-skipped-tests-20260525-r3
created_at: '2026-05-25T12:14:49Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture
summary: Checked current JUnit shards and remaining architecture skip-risk files after
  removing the env-var centralization skip; no additional current architecture skips
  were confirmed in run-20260525T143634, and the changed
  test_allowed_composition_files_still_exist case passed without skip.
---

# Episodic summary

## Task

- Title: Audit remaining skipped tests

## Outcome

- Checked current JUnit shards and remaining architecture skip-risk files after
  removing the env-var centralization skip; no additional current architecture
  skips were confirmed in run-20260525T143634, and the changed
  `test_allowed_composition_files_still_exist` case passed without skip.

## Lessons learned

- Scan the freshest completed JUnit run for `<skipped>` before changing tests:
  older run directories can contain accepted opt-in live API skips that are not
  current architecture skip-budget regressions.
