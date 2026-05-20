---
id: fix-test-structural-debt-neo4j-memory-sync
title: Split oversized neo4j_memory_sync test support module
task_id: fix-test-structural-debt-neo4j-memory-sync
created_at: '2026-05-20T05:14:48Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Split tests/testing_support/neo4j_memory_sync.py into support shards under
  tests/testing_support/neo4j_memory_sync_support, kept tests.testing_support.neo4j_memory_sync
  as a compatibility re-export shim, fixed shared helper exports and repo-root resolution
  after the split, and revalidated the structural-debt guard plus the full neo4j_memory_sync
  unit suite.
---

# Episodic summary

## Task

- Title: Split oversized neo4j_memory_sync test support module

## Outcome

- Split tests/testing_support/neo4j_memory_sync.py into support shards under tests/testing_support/neo4j_memory_sync_support, kept tests.testing_support.neo4j_memory_sync as a compatibility re-export shim, fixed shared helper exports and repo-root resolution after the split, and revalidated the structural-debt guard plus the full neo4j_memory_sync unit suite.

## Lessons learned

- Replace with durable follow-up if needed
