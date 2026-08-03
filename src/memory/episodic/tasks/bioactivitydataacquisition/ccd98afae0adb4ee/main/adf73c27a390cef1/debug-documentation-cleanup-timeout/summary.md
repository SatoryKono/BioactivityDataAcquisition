---
record_id: debug-documentation-cleanup-timeout
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 6a1b2de1b141d8fbcdec71c0b9c1f9b036c6b453
branch: main
worktree_id: ccd98afae0adb4ee
task_id: debug-documentation-cleanup-timeout
actor:
  runtime: codex
  agent: py-debug-bot
  model: null
created_at: '2026-07-31T18:59:04.831910+00:00'
source_refs:
- docs/00-project/ai/memory/agent-memory.md
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: fc40de2312982fc90e7f9483ce1cd5a683a91443847cc5d093ea5862f9662a07
id: debug-documentation-cleanup-timeout
title: Diagnose documentation cleanup inventory timeout using project venv
ttl_days: 14
confidence: episodic
summary: 'Recorded shared preference to use project venvs. Isolated inventory generator:
  direct WSL venv subprocess passes in 3.6s and build takes 6.3s; observed an orphaned
  Windows full-suite pytest process still alive after timeout, consistent with reader
  threads waiting for subprocess pipe EOF. Focused pytest validation was blocked while
  that orphan remained.'
---

# Episodic summary

## Task

- Title: Diagnose documentation cleanup inventory timeout using project venv

## Outcome

- Recorded shared preference to use project venvs. Isolated inventory generator: direct WSL venv subprocess passes in 3.6s and build takes 6.3s; observed an orphaned Windows full-suite pytest process still alive after timeout, consistent with reader threads waiting for subprocess pipe EOF. Focused pytest validation was blocked while that orphan remained.

## Lessons learned

- Replace with durable follow-up if needed
