---
record_id: codex-direct-ref-env
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 8c79a6cae7795e951bc833d4cf0b923774b9f8ae
branch: main
worktree_id: b5393af69d37a674
task_id: codex-direct-ref-env
actor:
  runtime: codex
  agent: py-config-bot
  model: null
created_at: '2026-08-16T14:30:25.552032+00:00'
source_refs:
- scripts/ai/codex/helper/ensure-codex-cli.sh
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 0318de4fe487a1097fc0e71f40e9e33a58b6165c097cda2e890a927ccaed159b
id: codex-direct-ref-env
title: Make direct codex launch Ref MCP authentication
ttl_days: 14
confidence: episodic
summary: Installed and validated a managed direct codex command shim that preserves
  native CLI arguments and loads only REF_TOOL_API_KEY from the repository env through
  the shared launcher helper.
---

# Episodic summary

## Task

- Title: Make direct codex launch Ref MCP authentication

## Outcome

- Installed and validated a managed direct codex command shim that preserves native CLI arguments and loads only REF_TOOL_API_KEY from the repository env through the shared launcher helper.

## Lessons learned

- Replace with durable follow-up if needed
