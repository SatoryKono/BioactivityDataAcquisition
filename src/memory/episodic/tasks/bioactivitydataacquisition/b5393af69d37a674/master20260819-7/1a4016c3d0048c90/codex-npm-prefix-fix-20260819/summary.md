---
record_id: codex-npm-prefix-fix-20260819
record_type: working
repo_id: bioactivitydataacquisition
git_commit: afd078ab38176954185fb9938db00f03e39b09ba
branch: master20260819-7
worktree_id: b5393af69d37a674
task_id: codex-npm-prefix-fix-20260819
actor:
  runtime: codex
  agent: codex
  model: gpt-5.6-sol
created_at: '2026-08-19T15:52:55.656590+00:00'
source_refs:
- scripts/ai/codex/helper/run-codex-impl.sh
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 279a99bf2e87623a959336dc97290fd6698cb6f8643e0fd0b4704d850030edc7
id: codex-npm-prefix-fix-20260819
title: Fix Codex managed npm prefix propagation
ttl_days: 14
confidence: episodic
summary: Propagated the managed npm prefix through the direct Codex shim path and
  added a regression assertion. Focused architecture tests, shell validation, Ruff,
  docs drift, and unsandboxed Codex Doctor passed. Repository-wide proof-or-stop returned
  STOP because concurrent unrelated governance/debt artifacts were stale and the shared
  worktree changed during receipt capture.
---

# Episodic summary

## Task

- Title: Fix Codex managed npm prefix propagation

## Outcome

- Propagated the managed npm prefix through the direct Codex shim path and added a regression assertion. Focused architecture tests, shell validation, Ruff, docs drift, and unsandboxed Codex Doctor passed. Repository-wide proof-or-stop returned STOP because concurrent unrelated governance/debt artifacts were stale and the shared worktree changed during receipt capture.

## Lessons learned

- Replace with durable follow-up if needed
