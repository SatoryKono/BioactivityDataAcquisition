---
id: neo4j-memory-failures-20260602
title: Fix neo4j memory support NameError failures
task_id: neo4j-memory-failures-20260602
created_at: '2026-06-02T08:17:02Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/testing_support/neo4j_memory_sync_support/common.py
summary: Expanded neo4j memory test-support common facade to re-export canonical sync
  symbols and required stdlib helpers; targeted NameError failures now pass.
---

# Episodic summary

## Task

- Title: Fix neo4j memory support NameError failures

## Outcome

- Expanded neo4j memory test-support common facade to re-export canonical sync symbols and required stdlib helpers; targeted NameError failures now pass.

## Lessons learned

- Replace with durable follow-up if needed
