---
id: fix-chembl-publication-replay-guard
title: Fix chembl_publication replay guard and Windows git provenance
task_id: fix-chembl-publication-replay-guard
created_at: '2026-05-15T18:20:22Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Allowed bounded live source runs without launch snapshots, added Windows
  git executable fallback, verified chembl_publication bootstrap passes under degraded_observable
  and fails under replay_ready only because source_revision_state is dirty.
---

# Episodic summary

## Task

- Title: Fix chembl_publication replay guard and Windows git provenance

## Outcome

- Allowed bounded live source runs without launch snapshots, added Windows git executable fallback, verified chembl_publication bootstrap passes under degraded_observable and fails under replay_ready only because source_revision_state is dirty.

## Lessons learned

- Replace with durable follow-up if needed
