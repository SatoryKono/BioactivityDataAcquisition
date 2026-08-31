---
record_id: zed-coverage-local-diagnosis-20260831
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 861056c1d34e15900a452f8fd3595496e2338ee1
branch: main
worktree_id: 7360d78d97884e9f
task_id: zed-coverage-local-diagnosis-20260831
actor:
  runtime: codex
  agent: codex
  model: null
created_at: '2026-08-31T13:16:17.711544+00:00'
source_refs:
- .zed\tasks.json
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: dfab23a9f0697f09f94142943008f4c1319fc787ccfdeb7218348374b31e496f
id: zed-coverage-local-diagnosis-20260831
title: Diagnose Coverage local estimate failure
ttl_days: 14
confidence: episodic
summary: 'DBG-001: Coverage local ran against a moving shared checkout. The Zed process
  started at 16:00:54, while reflog recorded commits, checkouts, reset, fast-forward,
  merges, and further commits during the same run. Collection passed; representative
  failure passed isolated with and without coverage; the full adapter subset passed
  with and without coverage. Existing HTML report was 94.58%, so the 85% threshold
  is ruled out. The active run is invalid evidence and must be rerun only after checkout/process
  activity is stable.'
---

# Episodic summary

## Task

- Title: Diagnose Coverage local estimate failure

## Outcome

- DBG-001: Coverage local ran against a moving shared checkout. The Zed process started at 16:00:54, while reflog recorded commits, checkouts, reset, fast-forward, merges, and further commits during the same run. Collection passed; representative failure passed isolated with and without coverage; the full adapter subset passed with and without coverage. Existing HTML report was 94.58%, so the 85% threshold is ruled out. The active run is invalid evidence and must be rerun only after checkout/process activity is stable.

## Lessons learned

- Replace with durable follow-up if needed
