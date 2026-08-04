---
id: sonar-nosonar
title: Close outstanding Sonar NOSONAR markers in neo4j sync script
source_refs:
- scripts/ops/neo4j_memory_sync.py
- src/memory/graph/sync_pkg/_core.py
- tests/unit/scripts/ops/neo4j_memory_sync/test_paths_and_connection.py
- tests/unit/scripts/ops/neo4j_memory_sync/test_snapshot_topology.py
summary: 'Added missing #NOSONAR comments for remaining Sonar findings in scripts/ops/neo4j_memory_sync.py
  and validated via compile + targeted tests.'
kind: incident
confidence: curated
last_verified: '2026-08-04T00:00:00Z'
promoted_from: /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/src/memory/episodic/summaries/sonar-nosonar.md
---

# Incident lesson

## Trigger pattern

> # Episodic summary
>
> ## Task
>
> - Title: Close outstanding Sonar NOSONAR markers in neo4j sync script
>
> ## Outcome
>
> - Added missing #NOSONAR comments for remaining Sonar findings in scripts/ops/neo4j_memory_sync.py and validated via compile + targeted tests.
>
> ## Lessons learned
>
> - Prevent Sonar suppression drift by pairing each `# NOSONAR` with a task-specific issue record and automated verification (`py_compile` + focused tests), then schedule periodic cleanup for transient suppressions.

## Response guidance

- Start from the cited runbook or operational source before improvising a fix.

## Durable lesson

- Keep this note aligned with recurring failure patterns only.
