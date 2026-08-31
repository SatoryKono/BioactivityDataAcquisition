---
record_id: neo4jmemory-repair-20260831
record_type: working
repo_id: bioactivitydataacquisition
git_commit: 1cbd13cf906b512664744555e342045453909204
branch: main
worktree_id: 7360d78d97884e9f
task_id: neo4jmemory-repair-20260831
actor:
  runtime: codex
  agent: codex
  model: gpt-5
created_at: '2026-08-31T11:01:11.127844+00:00'
source_refs:
- scripts/ai/mcp/mcp_neo4j_memory_wrapper.ps1
source_hashes: {}
trust: trusted_repository
security_class: internal
status: active
supersedes: []
schema_version: 1
content_digest: 7b89431d694f4d9479da4d929decdf5db350d0bd384b756bb8d47067d346a01a
id: neo4jmemory-repair-20260831
title: Repair Neo4jMemory
ttl_days: 14
confidence: episodic
summary: Restored Docker Desktop and healthy bioetl-neo4j, replaced stale direct Neo4jMemory
  registration with the pinned repository PowerShell wrapper, and verified Bolt plus
  MCP initialize/tools-list.
---

# Episodic summary

## Task

- Title: Repair Neo4jMemory

## Outcome

- Restored Docker Desktop and healthy bioetl-neo4j, replaced stale direct Neo4jMemory registration with the pinned repository PowerShell wrapper, and verified Bolt plus MCP initialize/tools-list.

## Lessons learned

- Replace with durable follow-up if needed
