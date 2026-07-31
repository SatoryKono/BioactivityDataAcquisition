---
record_id: fix-windows-module-coverage-git-pipe-timeout
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 6a1b2de1b141d8fbcdec71c0b9c1f9b036c6b453
branch: main
worktree_id: ccd98afae0adb4ee
task_id: fix-windows-module-coverage-git-pipe-timeout
actor:
  runtime: codex
  agent: py-debug-bot
  model: null
created_at: '2026-07-31T19:04:43.316270+00:00'
source_refs:
- tests/architecture/_module_coverage_inventory_support.py
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 1744fb6793d13f6d7e105eb5a5a7a5589b50456935ed6a3f4f69439a09b934f2
id: fix-windows-module-coverage-git-pipe-timeout
title: Fix Windows module coverage Git pipe timeout
ttl_days: 14
confidence: episodic
summary: Replaced capture_output Git guards with bounded temporary-file output to
  prevent inherited Windows pipe reader threads from hanging after timeout; added
  regression coverage.
---

# Episodic summary

## Task

- Title: Fix Windows module coverage Git pipe timeout

## Outcome

- Replaced capture_output Git guards with bounded temporary-file output to prevent inherited Windows pipe reader threads from hanging after timeout; added regression coverage.

## Lessons learned

- Replace with durable follow-up if needed
