---
record_id: fix-memory-wrapper-windows-path
record_type: working
repo_id: bioactivitydataacquisition
git_commit: fb47d2c8d1f3d14f0e45b5fc316a0ae7e408c79e
branch: main
worktree_id: ccd98afae0adb4ee
task_id: fix-memory-wrapper-windows-path
actor:
  runtime: unknown
  agent: memory-workflow
  model: null
created_at: '2026-07-30T08:01:37.230273+00:00'
source_refs:
- tests/unit/repo_backed/scripts/ai/mcp/test_memory_persistence_mode.py
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 27b46d3f2214b6310d9522d7d55e8c323f5815d0fd92938203c306b7b0be2e2a
id: fix-memory-wrapper-windows-path
title: Fix MCP memory wrapper test path portability
ttl_days: 14
confidence: episodic
summary: Changed both bash wrapper invocations in the MCP memory persistence-mode
  tests to use Path.as_posix(), preventing Windows backslashes from being consumed
  as bash escapes. Fourteen related tests and Ruff pass.
---

# Episodic summary

## Task

- Title: Fix MCP memory wrapper test path portability

## Outcome

- Changed both bash wrapper invocations in the MCP memory persistence-mode tests to use Path.as_posix(), preventing Windows backslashes from being consumed as bash escapes. Fourteen related tests and Ruff pass.

## Lessons learned

- Replace with durable follow-up if needed
