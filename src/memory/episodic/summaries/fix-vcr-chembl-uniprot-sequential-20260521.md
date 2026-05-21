---
id: fix-vcr-chembl-uniprot-sequential-20260521
title: Fix multi-provider VCR drift for chembl+uniprot sequential E2E
task_id: fix-vcr-chembl-uniprot-sequential-20260521
created_at: '2026-05-21T09:05:11Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Fixed E2E VCR cassette drift for chembl+uniprot sequential run by syncing
  the multi-provider cassette target interaction and restoring per-test cassette-dir
  resolution in e2e VCR fixtures.
---

# Episodic summary

## Task

- Title: Fix multi-provider VCR drift for chembl+uniprot sequential E2E

## Outcome

- Fixed E2E VCR cassette drift for chembl+uniprot sequential run by syncing the multi-provider cassette target interaction and restoring per-test cassette-dir resolution in e2e VCR fixtures.

## Lessons learned

- Replace with durable follow-up if needed
