---
record_id: deepwiki-devin-header-projection
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 524c5cf57aeab4678d4ce84973f2ce8c5d3f64c0
branch: main
worktree_id: ccd98afae0adb4ee
task_id: deepwiki-devin-header-projection
actor:
  runtime: codex
  agent: root
  model: null
created_at: '2026-07-31T07:42:07.157188+00:00'
source_refs:
- scripts/ai/codex/setup_mcp.py
- .devin/config.json
- tests/architecture/test_dev_setup_copilot_codex_mcp_consolidation.py
- docs/00-project/ai/mcp-token-configuration.md
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 709146b6b4807c9db97ee6a393025bec840e6fc1b08e99e7066cc0714f16965a
id: deepwiki-devin-header-projection
title: Fix DeepWiki Devin MCP projection
ttl_days: 14
confidence: episodic
summary: Added DeepWiki environment-header references to the canonical MCP generator,
  generalized Devin projection from env_http_headers to headers, updated tracked Devin
  config and architecture/token tests, and documented DeepWiki secret projection.
  MCP architecture suites and docs drift pass; full docs link scan was stopped after
  four minutes without output.
---

# Episodic summary

## Task

- Title: Fix DeepWiki Devin MCP projection

## Outcome

- Added DeepWiki environment-header references to the canonical MCP generator, generalized Devin projection from env_http_headers to headers, updated tracked Devin config and architecture/token tests, and documented DeepWiki secret projection. MCP architecture suites and docs drift pass; full docs link scan was stopped after four minutes without output.

## Lessons learned

- Replace with durable follow-up if needed
