---
record_id: mcp-singleton-multiclient-audit-20260804
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 472577b054a097dd85a559c2da2966f3c9c6f5a2
branch: fix/ci-audit-cycle-20260804
worktree_id: b5393af69d37a674
task_id: mcp-singleton-multiclient-audit-20260804
actor:
  runtime: codex
  agent: codex
  model: gpt-5
created_at: '2026-08-04T05:08:23.134621+00:00'
source_refs:
- scripts/ops/runtime/mcp/_materialize_shared_http_configs.py
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 8a626f635e5f4a31b8be35d54fda330ab4813a96e6cf0c7842a282910b214053
id: mcp-singleton-multiclient-audit-20260804
title: Audit singleton multi-client MCP runtime
ttl_days: 14
confidence: episodic
summary: Moved the singleton shared MCP plane to the current checkout, materialized
  the full shared HTTP profile for local clients, restored neo4j-memory from a corrupt
  npm cache entry, preserved remote auth env mappings, and verified all 19 local endpoints
  plus remote Ref/DeepWiki.
---

# Episodic summary

## Task

- Title: Audit singleton multi-client MCP runtime

## Outcome

- Moved the singleton shared MCP plane to the current checkout, materialized the full shared HTTP profile for local clients, restored neo4j-memory from a corrupt npm cache entry, preserved remote auth env mappings, and verified all 19 local endpoints plus remote Ref/DeepWiki.

## Lessons learned

- Replace with durable follow-up if needed
