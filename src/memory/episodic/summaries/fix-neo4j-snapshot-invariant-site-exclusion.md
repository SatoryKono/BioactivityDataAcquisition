---
id: fix-neo4j-snapshot-invariant-site-exclusion
title: Fix Neo4j snapshot invariant site exclusions
task_id: fix-neo4j-snapshot-invariant-site-exclusion
created_at: '2026-05-21T09:04:16Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/memory/graph/sync.py
summary: Added docs/site to Neo4j memory sync file-structure exclusions and path-leak
  invariants so generated MkDocs site artifacts do not pollute snapshot support tests.
---

# Episodic summary

## Task

- Title: Fix Neo4j snapshot invariant site exclusions

## Outcome

- Added docs/site to Neo4j memory sync file-structure exclusions and path-leak invariants so generated MkDocs site artifacts do not pollute snapshot support tests.

## Lessons learned

- Replace with durable follow-up if needed
