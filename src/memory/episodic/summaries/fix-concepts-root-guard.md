---
id: fix-concepts-root-guard
title: Fix concepts root guard git ls-files failure
task_id: fix-concepts-root-guard
created_at: '2026-05-21T10:55:48Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Replaced Windows-fragile git ls-files concepts root guard with a direct filesystem
  invariant asserting root concepts/ does not exist.
---

# Episodic summary

## Task

- Title: Fix concepts root guard git ls-files failure

## Outcome

- Replaced Windows-fragile git ls-files concepts root guard with a direct filesystem invariant asserting root concepts/ does not exist.

## Lessons learned

- Replace with durable follow-up if needed
