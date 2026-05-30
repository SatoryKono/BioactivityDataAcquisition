---
id: fix-neo4j-memory-audit-fast-audit-fixture
title: Fix targeted sync fast-audit fixture failure
task_id: fix-neo4j-memory-audit-fast-audit-fixture
created_at: '2026-05-30T08:14:51Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/memory/graph/sync_pkg/cli.py
summary: Changed sync CLI to dispatch snapshot/audit helpers through memory.graph.sync_pkg._core
  at call time so test monkeypatches and targeted-sync behavior are respected without
  loading real evidence files from temporary roots.
---

# Episodic summary

## Task

- Title: Fix targeted sync fast-audit fixture failure

## Outcome

- Changed sync CLI to dispatch snapshot/audit helpers through memory.graph.sync_pkg._core at call time so test monkeypatches and targeted-sync behavior are respected without loading real evidence files from temporary roots.

## Lessons learned

- Replace with durable follow-up if needed
