---
record_id: mcp-single-shared-runtime-audit
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 25936f127e43478399f927861acca5f5dcd0f9de
branch: main
worktree_id: b5393af69d37a674
task_id: mcp-single-shared-runtime-audit
actor:
  runtime: codex
  agent: py-config-bot
  model: gpt-5
created_at: '2026-08-04T07:46:03.336406+00:00'
source_refs:
- scripts/ops/runtime/mcp/shared-servers.json
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: eed8ae77aa32ea94f6c68531a8734cf1aa1f4f5827ec73d6a7155ff10a5a6ced
id: mcp-single-shared-runtime-audit
title: MCP singleton shared runtime audit
ttl_days: 14
confidence: episodic
summary: Verified 19 local singleton MCP endpoints and 2 remote MCP endpoints across
  8 clients; replaced empty Docker Mermaid catalog runtime with pinned mcp-mermaid@0.4.1
  Windows-native streaming backend; validated stable PID reuse and protocol tools.
---

# Episodic summary

## Task

- Title: MCP singleton shared runtime audit

## Outcome

- Verified 19 local singleton MCP endpoints and 2 remote MCP endpoints across 8 clients; replaced empty Docker Mermaid catalog runtime with pinned mcp-mermaid@0.4.1 Windows-native streaming backend; validated stable PID reuse and protocol tools.

## Lessons learned

- Replace with durable follow-up if needed
