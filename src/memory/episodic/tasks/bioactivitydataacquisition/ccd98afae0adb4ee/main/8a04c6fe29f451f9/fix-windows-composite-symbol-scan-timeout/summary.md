---
record_id: fix-windows-composite-symbol-scan-timeout
record_type: working
repo_id: bioactivitydataacquisition
git_commit: b77ed7059d77d9b7beb2f77fe6de4724c6dc708f
branch: main
worktree_id: ccd98afae0adb4ee
task_id: fix-windows-composite-symbol-scan-timeout
actor:
  runtime: codex
  agent: py-debug-bot
  model: null
created_at: '2026-07-31T18:51:25.591937+00:00'
source_refs:
- tests/architecture/test_composite_canonical_surfaces.py
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 5766c74c7f46135c380b28f9f066bd240954e28ffc96249dc8777b8aebe0557d
id: fix-windows-composite-symbol-scan-timeout
title: Fix Windows composite symbol scan timeout
ttl_days: 14
confidence: episodic
summary: Changed Windows composite documentation symbol scanning to prefer ripgrep
  and bounded each scanner to 20 seconds so fallback completes within pytest's 60-second
  budget; added regression guards.
---

# Episodic summary

## Task

- Title: Fix Windows composite symbol scan timeout

## Outcome

- Changed Windows composite documentation symbol scanning to prefer ripgrep and bounded each scanner to 20 seconds so fallback completes within pytest's 60-second budget; added regression guards.

## Lessons learned

- Replace with durable follow-up if needed
