---
id: memory-tests-fix-20260524
title: Run and fix memory tests
task_id: memory-tests-fix-20260524
created_at: '2026-05-24T17:39:42Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/memory/test_tooling.py
- tests/unit/memory/test_validate.py
- tests/unit/scripts/ops/neo4j_memory_sync/test_snapshot_invariants.py
- tests/testing_support/neo4j_memory_sync_support/snapshot_topology.py
- src/memory/graph/sync.py
summary: Stabilized memory test execution by avoiding full memory corpus copies in
  unit tests, restoring timeout marks on Neo4j memory sync wrappers, making sync statement
  metadata test use a minimal graph, and caching source path kind checks in memory
  graph snapshot linking. Verified unit memory, integration memory, script/ops memory,
  smoke memory, and the combined explicit memory test set.
---

# Episodic summary

## Task

- Title: Run and fix memory tests

## Outcome

- Stabilized memory test execution by avoiding full memory corpus copies in unit tests, restoring timeout marks on Neo4j memory sync wrappers, making sync statement metadata test use a minimal graph, and caching source path kind checks in memory graph snapshot linking. Verified unit memory, integration memory, script/ops memory, smoke memory, and the combined explicit memory test set.

## Lessons learned

- Replace with durable follow-up if needed
