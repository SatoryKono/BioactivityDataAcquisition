---
record_id: fix-mounted-worktree-git-grep-timeout
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 773ad7b5145034ce18a0c3eb75b0ab475912528e
branch: main
worktree_id: ccd98afae0adb4ee
task_id: fix-mounted-worktree-git-grep-timeout
actor:
  runtime: codex
  agent: py-debug-bot
  model: null
created_at: '2026-07-31T19:28:21.305901+00:00'
source_refs:
- tests/architecture/test_mounted_worktree_skip_policy.py
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: f7a551b6042accdb40a9adbfb4dac96373b0c60fabb3d2424fbe004616f54be1
id: fix-mounted-worktree-git-grep-timeout
title: Fix mounted worktree Git grep reader-thread timeout
ttl_days: 14
confidence: episodic
summary: Changed the mounted-worktree architecture guard to redirect Git grep stdout/stderr
  to local temporary files, disable optional Git locks, and avoid subprocess PIPE
  reader threads. Added regression coverage. The focused Windows guard passes in 0.84s
  and all three previously timing-out tests pass together.
---

# Episodic summary

## Task

- Title: Fix mounted worktree Git grep reader-thread timeout

## Outcome

- Changed the mounted-worktree architecture guard to redirect Git grep stdout/stderr to local temporary files, disable optional Git locks, and avoid subprocess PIPE reader threads. Added regression coverage. The focused Windows guard passes in 0.84s and all three previously timing-out tests pass together.

## Lessons learned

- Replace with durable follow-up if needed
