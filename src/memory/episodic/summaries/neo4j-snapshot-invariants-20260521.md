---
id: neo4j-snapshot-invariants-20260521
title: Fix neo4j snapshot invariant regression
task_id: neo4j-snapshot-invariants-20260521
created_at: '2026-05-21T09:09:52Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Investigated the neo4j snapshot invariant failure, isolated the slow normalization-evidence
  import path, and re-ran the failing snapshot_invariants shard; the invariant is
  clean on the current Linux checkout and no code change was required.
---

# Episodic summary

## Task

- Title: Fix neo4j snapshot invariant regression

## Outcome

- Investigated the neo4j snapshot invariant failure, isolated the slow normalization-evidence import path, and re-ran the failing snapshot_invariants shard; the invariant is clean on the current Linux checkout and no code change was required.

## Lessons learned

- Replace with durable follow-up if needed
