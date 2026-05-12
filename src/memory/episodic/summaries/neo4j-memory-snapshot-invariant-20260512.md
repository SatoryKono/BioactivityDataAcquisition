---
id: neo4j-memory-snapshot-invariant-20260512
title: Fix Neo4j memory snapshot invariant
task_id: neo4j-memory-snapshot-invariant-20260512
created_at: '2026-05-12T18:00:09Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Fixed Neo4j memory snapshot invariant leak by excluding docs/02-architecture/diagrams/png
  from memory graph file-structure surfaces in runtime defaults plus canonical and
  quality mapping files. Also fixed class suffix naming gate by renaming FieldPriorityScan
  to FieldPriorityScanResult. Validated targeted Neo4j invariant, preflight validator,
  naming conventions, py_compile, and ruff on changed Python files.
---

# Episodic summary

## Task

- Title: Fix Neo4j memory snapshot invariant

## Outcome

- Fixed Neo4j memory snapshot invariant leak by excluding docs/02-architecture/diagrams/png from memory graph file-structure surfaces in runtime defaults plus canonical and quality mapping files. Also fixed class suffix naming gate by renaming FieldPriorityScan to FieldPriorityScanResult. Validated targeted Neo4j invariant, preflight validator, naming conventions, py_compile, and ruff on changed Python files.

## Lessons learned

- Replace with durable follow-up if needed
