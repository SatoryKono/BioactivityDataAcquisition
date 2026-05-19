---
id: crossref-year-fixture-sync-20260519
title: Sync CrossRef year-validation fixture with schema sidecars
task_id: crossref-year-fixture-sync-20260519
created_at: '2026-05-19T12:04:34Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/domain/schemas/test_year_validation.py
summary: Updated CrossRef year-validation test fixture to include nullable structured-payload
  sidecar fields author_details_raw_json, author_details_canonical_json, references_raw_json,
  and references_canonical_json required by the current Pandera schema.
---

# Episodic summary

## Task

- Title: Sync CrossRef year-validation fixture with schema sidecars

## Outcome

- Updated CrossRef year-validation test fixture to include nullable structured-payload sidecar fields author_details_raw_json, author_details_canonical_json, references_raw_json, and references_canonical_json required by the current Pandera schema.

## Lessons learned

- Replace with durable follow-up if needed
