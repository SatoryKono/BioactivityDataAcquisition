---
id: documentation-sync-ports-count-20260601
title: Fix domain ports count documentation drift
task_id: documentation-sync-ports-count-20260601
created_at: '2026-06-01T06:54:41Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_documentation_sync.py
summary: Updated domain-layer documentation and merged documentation mirror from 17
  to 18 top-level domain ports modules after live code scan showed protein_classification.py
  in src/bioetl/domain/ports. Revalidated test_ports_count_matches_docs and rescanned
  docs/reports for stale count references.
---

# Episodic summary

## Task

- Title: Fix domain ports count documentation drift

## Outcome

- Updated domain-layer documentation and merged documentation mirror from 17 to 18 top-level domain ports modules after live code scan showed protein_classification.py in src/bioetl/domain/ports. Revalidated test_ports_count_matches_docs and rescanned docs/reports for stale count references.

## Lessons learned

- Replace with durable follow-up if needed
