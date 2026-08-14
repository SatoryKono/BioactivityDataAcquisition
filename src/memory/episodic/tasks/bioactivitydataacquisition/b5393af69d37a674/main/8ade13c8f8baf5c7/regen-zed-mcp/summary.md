---
record_id: regen-zed-mcp
record_type: working
repo_id: bioactivitydataacquisition
git_commit: afbb8f61b4562caff369f90221f4080f9f4d9983
branch: main
worktree_id: b5393af69d37a674
task_id: regen-zed-mcp
actor:
  runtime: grok
  agent: grok-4.6
  model: null
created_at: '2026-08-14T10:02:16.874327+00:00'
source_refs:
- <add-source-ref>
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: dfe8ca22321490b2a0c4853e8e7c0bdc7184d568521d8898bcf217ff2cff3351
id: regen-zed-mcp
title: Regenerate .zed/mcp.json from .mcp.json
ttl_days: 14
confidence: episodic
summary: Copied canonical .mcp.json (stdio command wrappers) over drifted HTTP .zed/mcp.json.
  Architecture consolidation test and setup_mcp --check now pass.
---

# Episodic summary

## Task

- Title: Regenerate .zed/mcp.json from .mcp.json

## Outcome

- Copied canonical .mcp.json (stdio command wrappers) over drifted HTTP .zed/mcp.json. Architecture consolidation test and setup_mcp --check now pass.

## Lessons learned

- Replace with durable follow-up if needed
