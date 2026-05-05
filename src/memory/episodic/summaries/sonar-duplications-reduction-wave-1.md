---
id: sonar-duplications-reduction-wave-1
title: Reduce Sonar duplications wave 1
task_id: sonar-duplications-reduction-wave-1
created_at: '2026-05-05T08:40:25Z'
ttl_days: 14
confidence: episodic
source_refs:
- docs/00-project/ai/memory/memory-py-architecture-debt-bot.md
summary: Cut the largest duplication hotspots by converting scripts.ops.neo4j_memory_sync
  into a compatibility alias over memory.graph.sync, deleting the fully duplicated
  Grafana timing test module after moving its unique overview-range assertion into
  the canonical grafana contract suite, and extracting shared batch-transformer test
  fixtures into tests.unit.application.core.transformer_test_support before resyncing
  architecture dependency docs.
---

# Episodic summary

## Task

- Title: Reduce Sonar duplications wave 1

## Outcome

- Cut the largest duplication hotspots by converting scripts.ops.neo4j_memory_sync into a compatibility alias over memory.graph.sync, deleting the fully duplicated Grafana timing test module after moving its unique overview-range assertion into the canonical grafana contract suite, and extracting shared batch-transformer test fixtures into tests.unit.application.core.transformer_test_support before resyncing architecture dependency docs.

## Lessons learned

- Replace with durable follow-up if needed
