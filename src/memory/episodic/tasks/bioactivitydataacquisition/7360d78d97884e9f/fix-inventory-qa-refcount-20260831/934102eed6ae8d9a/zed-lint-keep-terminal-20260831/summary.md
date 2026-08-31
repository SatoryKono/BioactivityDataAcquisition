---
record_id: zed-lint-keep-terminal-20260831
record_type: working
repo_id: bioactivitydataacquisition
git_commit: dff2908014b94dd11db8ef06510d87f65fcd69ee
branch: fix/inventory-qa-refcount-20260831
worktree_id: 7360d78d97884e9f
task_id: zed-lint-keep-terminal-20260831
actor:
  runtime: codex
  agent: codex
  model: null
created_at: '2026-08-31T12:56:13.050568+00:00'
source_refs:
- .zed\tasks.json
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 16f1acaaf841e43eaa7f51389f4e03fa50583f34fe91983dee529ddadf2caec0
id: zed-lint-keep-terminal-20260831
title: Keep Zed Check lint terminal visible
ttl_days: 14
confidence: episodic
summary: Changed only the Zed Check lint task from hide=on_success to hide=never and
  updated its repo-backed contract while preserving auto-hide for MCP manifests and
  environment verification. JSON parse, 20 Zed workspace tests, targeted Ruff, exact
  Check lint, and git diff check all passed. No generated artifacts or runtime mirrors
  were involved; technical debt unchanged.
---

# Episodic summary

## Task

- Title: Keep Zed Check lint terminal visible

## Outcome

- Changed only the Zed Check lint task from hide=on_success to hide=never and updated its repo-backed contract while preserving auto-hide for MCP manifests and environment verification. JSON parse, 20 Zed workspace tests, targeted Ruff, exact Check lint, and git diff check all passed. No generated artifacts or runtime mirrors were involved; technical debt unchanged.

## Lessons learned

- Replace with durable follow-up if needed
