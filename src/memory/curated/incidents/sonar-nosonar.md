---
id: sonar-nosonar
title: Close outstanding Sonar NOSONAR markers in neo4j sync script
kind: incident
source_refs:
- scripts/ops/neo4j_memory_sync.py
- src/memory/README.md
- src/memory/graph/sync_pkg/_core.py
confidence: curated
last_verified: '2026-08-04T00:00:00Z'
summary: Pair each Sonar NOSONAR suppression with a task-specific issue record and automated verification, then schedule periodic cleanup of transient suppressions.
promoted_from: unspecified
---

# Incident lesson

## Trigger pattern

- Sonar findings accumulate on neo4j memory sync surfaces when suppressions drift out of sync with the canonical implementation path.
- The compatibility shim `scripts/ops/neo4j_memory_sync.py` delegates to `memory.graph.sync`; durable logic lives under `src/memory/graph/`.

## Response guidance

- Start from the cited sync surface and targeted tests before improvising a fix.
- Prefer removing suppressions when the underlying issue is fixed; keep `# NOSONAR` only with an explicit linked task and verification.

## Durable lesson

- Prevent Sonar suppression drift by pairing each `# NOSONAR` with a task-specific issue record and automated verification (`py_compile` + focused tests), then schedule periodic cleanup for transient suppressions.
