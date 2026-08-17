---
record_id: fix-codex-mcp-shared-autostart-20260817
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 06e86a44273d9f5dfd45129aca1ec6b5ca2124d2
branch: feat/grafana-p2-first-window-copy-2
worktree_id: b5393af69d37a674
task_id: fix-codex-mcp-shared-autostart-20260817
actor:
  runtime: codex
  agent: py-config-bot
  model: null
created_at: '2026-08-17T09:29:45.763221+00:00'
source_refs:
- scripts/ai/codex/helper/run-codex-impl.sh
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 5cc1fdd151d955fbbf7caf42f422895b736530d4639e33b8363660659a9edf03
id: fix-codex-mcp-shared-autostart-20260817
title: Fix Codex shared MCP autostart
ttl_days: 14
confidence: episodic
summary: Managed codex shim now reconciles MCP before direct exec, launcher timeout
  ownership is delegated to ensure-mcp, regression tests and docs were updated, and
  stable shared MCP readiness is 9/9.
---

# Episodic summary

## Task

- Title: Fix Codex shared MCP autostart

## Outcome

- Managed codex shim now reconciles MCP before direct exec, launcher timeout ownership is delegated to ensure-mcp, regression tests and docs were updated, and stable shared MCP readiness is 9/9.

## Lessons learned

- Replace with durable follow-up if needed
