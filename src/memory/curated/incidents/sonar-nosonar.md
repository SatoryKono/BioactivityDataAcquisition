---
id: sonar-nosonar
title: Close outstanding Sonar NOSONAR markers in neo4j sync script
source_refs:
- src/memory/README.md
summary: 'Added missing #NOSONAR comments for remaining Sonar findings in scripts/ops/neo4j_memory_sync.py
  and validated via compile + targeted tests.'
kind: incident
confidence: curated
last_verified: '2026-05-04T17:40:25Z'
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
