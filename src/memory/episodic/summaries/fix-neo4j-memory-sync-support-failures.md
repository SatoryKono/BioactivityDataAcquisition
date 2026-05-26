---
id: fix-neo4j-memory-sync-support-failures
title: Fix Neo4j memory sync support audit runtime tests
task_id: fix-neo4j-memory-sync-support-failures
created_at: '2026-05-26T06:13:54Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/testing_support/neo4j_memory_sync_support/audit_runtime_and_transport.py
summary: Updated Neo4j memory sync support tests to patch the canonical memory.graph.sync_pkg._core
  module instead of scripts.memory.sync facade aliases, preventing support/unit tests
  from reaching a real localhost Neo4j endpoint or real repo filesystem scans when
  stubs are intended. Validated Windows targeted failures, full audit_runtime_and_transport,
  targeted_apply_and_filters, snapshot_topology, py_compile, and WSL targeted failures.
---

# Episodic summary

## Task

- Title: Fix Neo4j memory sync support audit runtime tests

## Outcome

- Updated Neo4j memory sync support tests to patch the canonical memory.graph.sync_pkg._core module instead of scripts.memory.sync facade aliases, preventing support/unit tests from reaching a real localhost Neo4j endpoint or real repo filesystem scans when stubs are intended. Validated Windows targeted failures, full audit_runtime_and_transport, targeted_apply_and_filters, snapshot_topology, py_compile, and WSL targeted failures.

## Lessons learned

- Replace with durable follow-up if needed
