---
id: neo4j-memory-sync-partition-by-20260508
title: Fix memory sync and tooling import regressions
task_id: neo4j-memory-sync-partition-by-20260508
created_at: '2026-05-08T08:08:03Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/memory/graph/sync.py
- scripts/memory/__init__.py
- tests/testing_support/neo4j_memory_sync.py
- tests/unit/memory/test_tooling.py
summary: Fixed Neo4j memory snapshot storage sink extraction for top-level entity
  sink configs and corrected Windows-like memory tooling import precedence when scripts
  precedes src on PYTHONPATH. Updated regression expectations for projected storage-field
  drift classification.
---

# Episodic summary

## Task

- Title: Fix memory sync and tooling import regressions

## Outcome

- Fixed Neo4j memory snapshot storage sink extraction for top-level entity sink configs and corrected Windows-like memory tooling import precedence when scripts precedes src on PYTHONPATH. Updated regression expectations for projected storage-field drift classification.

## Lessons learned

- Replace with durable follow-up if needed
