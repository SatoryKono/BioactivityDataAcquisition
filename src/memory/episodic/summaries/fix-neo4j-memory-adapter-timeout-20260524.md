---
id: fix-neo4j-memory-adapter-timeout-20260524
title: Fix neo4j memory MCP adapter smoke timeout
task_id: fix-neo4j-memory-adapter-timeout-20260524
created_at: '2026-05-24T13:48:25Z'
ttl_days: 14
confidence: episodic
source_refs:
- scripts/ai/mcp/neo4j_memory_mcp_adapter.py
summary: Adjusted adapter shutdown sequencing to wait for server->client and stderr
  pump threads before exiting, reducing race-driven loss of final framed responses
  on slower Windows runners.
---

# Episodic summary

## Task

- Title: Fix neo4j memory MCP adapter smoke timeout

## Outcome

- Adjusted adapter shutdown sequencing to wait for server->client and stderr pump threads before exiting, reducing race-driven loss of final framed responses on slower Windows runners.

## Lessons learned

- Replace with durable follow-up if needed
