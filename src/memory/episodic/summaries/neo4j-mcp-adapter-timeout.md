---
id: neo4j-mcp-adapter-timeout
title: fix-neo4j-memory-mcp-adapter-timeout
task_id: neo4j-mcp-adapter-timeout
created_at: '2026-05-25T04:00:52Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/scripts/ops/test_neo4j_memory_mcp_adapter.py
summary: Hardened Neo4j memory MCP adapter bridge unit test against Windows subprocess
  startup jitter by increasing the framed adapter smoke timeout from 15s to 45s. The
  bridge logic passed on WSL and Windows; no adapter protocol code changed.
---

# Episodic summary

## Task

- Title: fix-neo4j-memory-mcp-adapter-timeout

## Outcome

- Hardened Neo4j memory MCP adapter bridge unit test against Windows subprocess startup jitter by increasing the framed adapter smoke timeout from 15s to 45s. The bridge logic passed on WSL and Windows; no adapter protocol code changed.

## Lessons learned

- Replace with durable follow-up if needed
