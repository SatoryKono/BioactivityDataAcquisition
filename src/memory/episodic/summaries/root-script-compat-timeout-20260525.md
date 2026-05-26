---
id: root-script-compat-timeout-20260525
title: Fix root script compatibility scanner timeout
task_id: root-script-compat-timeout-20260525
created_at: '2026-05-25T18:26:47Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/helpers/git_index_scan.py
summary: 'Fixed git-index scan helper timeout path for Windows architecture tests:
  broad git grep with many pathspecs now uses batched grep first on Windows, git_tracked_files
  no longer stats every tracked path, and targeted WSL/Windows architecture tests
  pass.'
---

# Episodic summary

## Task

- Title: Fix root script compatibility scanner timeout

## Outcome

- Fixed git-index scan helper timeout path for Windows architecture tests: broad git grep with many pathspecs now uses batched grep first on Windows, git_tracked_files no longer stats every tracked path, and targeted WSL/Windows architecture tests pass.

## Lessons learned

- Replace with durable follow-up if needed
