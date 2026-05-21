---
id: fix-neo4j-snapshot-invariants-20260521
title: Fix Neo4j memory snapshot invariant drift
task_id: fix-neo4j-snapshot-invariants-20260521
created_at: '2026-05-21T08:53:59Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/memory/graph/sync.py
- src/memory/graph/mappings.yaml
- configs/quality/neo4j_memory_mapping.yaml
summary: Reduced Neo4j snapshot build overhead by skipping git history sweeps for
  untracked paths, excluded generated memory/site artifact trees from snapshot file-structure
  policy, and fixed the confirmed docs/site invariant leak while validating related
  helper regressions.
---

# Episodic summary

## Task

- Title: Fix Neo4j memory snapshot invariant drift

## Outcome

- Reduced Neo4j snapshot build overhead by skipping git history sweeps for untracked paths, excluded generated memory/site artifact trees from snapshot file-structure policy, and fixed the confirmed docs/site invariant leak while validating related helper regressions.

## Lessons learned

- Replace with durable follow-up if needed
