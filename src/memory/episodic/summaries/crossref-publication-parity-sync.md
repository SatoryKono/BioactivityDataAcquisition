---
id: crossref-publication-parity-sync
title: Assess CrossRef publication parity snapshot drift
task_id: crossref-publication-parity-sync
created_at: '2026-05-19T10:31:36Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/fixtures/snapshots/publication_transformers/crossref_publication_silver.json
summary: Updated the CrossRef publication parity snapshot to include structured sidecar
  fields author_details_canonical_json, author_details_raw_json, references_canonical_json,
  and references_raw_json, along with the resulting deterministic content_hash change.
---

# Episodic summary

## Task

- Title: Assess CrossRef publication parity snapshot drift

## Outcome

- Updated the CrossRef publication parity snapshot to include structured sidecar fields author_details_canonical_json, author_details_raw_json, references_canonical_json, and references_raw_json, along with the resulting deterministic content_hash change.

## Lessons learned

- Replace with durable follow-up if needed
