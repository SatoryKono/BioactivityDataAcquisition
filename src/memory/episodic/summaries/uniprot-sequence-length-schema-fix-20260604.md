---
id: uniprot-sequence-length-schema-fix-20260604
title: Fix UniProt sequence_length schema validation
task_id: uniprot-sequence-length-schema-fix-20260604
created_at: '2026-06-04T15:22:23Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Investigated UniProt shard sequence_length validation failure; reproduced
  current state on Linux and Windows interpreters and all tests passed, so no code
  changes were required. Likely stale failure or environment drift.
---

# Episodic summary

## Task

- Title: Fix UniProt sequence_length schema validation

## Outcome

- Investigated UniProt shard sequence_length validation failure; reproduced current state on Linux and Windows interpreters and all tests passed, so no code changes were required. Likely stale failure or environment drift.

## Lessons learned

- Replace with durable follow-up if needed
