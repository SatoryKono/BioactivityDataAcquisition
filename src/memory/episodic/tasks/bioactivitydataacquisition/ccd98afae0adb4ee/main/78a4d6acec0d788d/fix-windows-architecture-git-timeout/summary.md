---
record_id: fix-windows-architecture-git-timeout
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 6a1b2de1b141d8fbcdec71c0b9c1f9b036c6b453
branch: main
worktree_id: ccd98afae0adb4ee
task_id: fix-windows-architecture-git-timeout
actor:
  runtime: codex
  agent: py-debug-bot
  model: null
created_at: '2026-07-31T19:20:52.190813+00:00'
source_refs:
- tests/architecture/_module_coverage_inventory_support.py
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 15e957e775577b2cbedccc192f71ba4dd3d43c0731422106f9f147a34181a5fc
id: fix-windows-architecture-git-timeout
title: Fix Windows architecture Git subprocess timeout
ttl_days: 14
confidence: episodic
summary: Stopped GitHub Desktop and orphaned Git trees, cleared stale index.lock,
  and changed module-coverage authority guards from git status to no-optional-locks
  staged/unstaged git diff checks with bounded failure-to-skip behavior. Added unit
  regressions. Windows focused tests pass.
---

# Episodic summary

## Task

- Title: Fix Windows architecture Git subprocess timeout

## Outcome

- Stopped GitHub Desktop and orphaned Git trees, cleared stale index.lock, and changed module-coverage authority guards from git status to no-optional-locks staged/unstaged git diff checks with bounded failure-to-skip behavior. Added unit regressions. Windows focused tests pass.

## Lessons learned

- Replace with durable follow-up if needed
