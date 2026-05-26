---
id: retest-application-services-lazy-facade-tests-scan-20260526
title: Retest application services lazy facade test scan
task_id: retest-application-services-lazy-facade-tests-scan-20260526
created_at: '2026-05-26T03:49:39Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_application_services_lazy_facade_governance.py
summary: Retested the reported application-services lazy facade governance failure.
  The workspace file already contains the bounded rg/git/Python-subprocess scan fallback,
  while the reported traceback matches the pre-fallback helper text and line layout.
  Windows targeted test, full architecture file, and forced no-rg/no-git fallback
  for ROOT/tests all pass on the current file.
---

# Episodic summary

## Task

- Title: Retest application services lazy facade test scan

## Outcome

- Retested the reported application-services lazy facade governance failure. The workspace file already contains the bounded rg/git/Python-subprocess scan fallback, while the reported traceback matches the pre-fallback helper text and line layout. Windows targeted test, full architecture file, and forced no-rg/no-git fallback for ROOT/tests all pass on the current file.

## Lessons learned

- When a user-provided traceback still contains the old helper ordering and
  assertion text, verify the workspace file and rerun the exact Windows test
  before making another code change.
