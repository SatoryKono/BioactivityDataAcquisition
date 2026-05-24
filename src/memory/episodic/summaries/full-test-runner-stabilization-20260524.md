---
id: full-test-runner-stabilization-20260524
title: Stabilize BioETL test runner and full suite
task_id: full-test-runner-stabilization-20260524
created_at: '2026-05-24T16:24:26Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/quality/pytest_shards.yaml
summary: 'Stabilized pytest sharded runner partially: fixed S2 composition/interfaces
  xdist instability by serializing the shard, added bounded test-health rollup timeout,
  removed UTF-8 BOM causing architecture AST SyntaxError, aligned storage bootstrap
  governance test with removed legacy adapter shim, split overloaded S7 architecture-a
  shard into smaller a/a2/a3 inventory entries, and validated runner inventory/list
  plus S7 architecture-a. Full suite could not be completed because concurrent Codex
  sessions kept launching pytest/snapshot jobs in the same checkout and /tmp/bioetl-test-runner,
  causing harness sessions to terminate without JUnit/final stdout.'
---

# Episodic summary

## Task

- Title: Stabilize BioETL test runner and full suite

## Outcome

- Stabilized pytest sharded runner partially: fixed S2 composition/interfaces xdist instability by serializing the shard, added bounded test-health rollup timeout, removed UTF-8 BOM causing architecture AST SyntaxError, aligned storage bootstrap governance test with removed legacy adapter shim, split overloaded S7 architecture-a shard into smaller a/a2/a3 inventory entries, and validated runner inventory/list plus S7 architecture-a. Full suite could not be completed because concurrent Codex sessions kept launching pytest/snapshot jobs in the same checkout and /tmp/bioetl-test-runner, causing harness sessions to terminate without JUnit/final stdout.

## Lessons learned

- Replace with durable follow-up if needed
