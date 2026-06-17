---
id: dbg-neo4j-memory-adapter
title: Debug neo4j memory MCP adapter test
task_id: dbg-neo4j-memory-adapter
created_at: '2026-06-17T06:02:55Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/scripts/ops/test_neo4j_memory_mcp_adapter.py
summary: Marked the repo-backed neo4j-memory MCP adapter tests as serial to avoid
  Windows parallel runner socket-buffer setup failures.
---

# Episodic summary

## Task

- Title: Debug neo4j memory MCP adapter test

## Outcome

- Marked the repo-backed neo4j-memory MCP adapter tests as serial to avoid Windows parallel runner socket-buffer setup failures.

## Lessons learned

- Replace with durable follow-up if needed
