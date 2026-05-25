---
id: neo4j-snapshot-path-kind-timeout
title: fix-neo4j-memory-snapshot-path-kind-timeout
task_id: neo4j-snapshot-path-kind-timeout
created_at: '2026-05-25T03:50:01Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/memory/graph/sync.py
- src/memory/tooling/workflow.py
summary: Reduced Neo4j memory snapshot timeout risk by removing per-source_path filesystem
  stat calls from source-backed file-structure linking, using materialized file/directory
  surfaces instead; made Python AST parsing read-first to avoid redundant is_file
  metadata calls; changed normalization evidence snapshot enrichment to use shipped
  normalization profile registry instead of building the full docs matrix; fixed memory
  workflow note writing prerequisite. Targeted snapshot invariant and topology checks
  pass.
---

# Episodic summary

## Task

- Title: fix-neo4j-memory-snapshot-path-kind-timeout

## Outcome

- Reduced Neo4j memory snapshot timeout risk by removing per-source_path filesystem stat calls from source-backed file-structure linking, using materialized file/directory surfaces instead; made Python AST parsing read-first to avoid redundant is_file metadata calls; changed normalization evidence snapshot enrichment to use shipped normalization profile registry instead of building the full docs matrix; fixed memory workflow note writing prerequisite. Targeted snapshot invariant and topology checks pass.

## Lessons learned

- Replace with durable follow-up if needed
