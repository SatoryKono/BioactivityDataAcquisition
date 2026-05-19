---
id: fix-uniprot-transformer-raw-fields
title: Fix UniProt transformer raw structured payload fields
task_id: fix-uniprot-transformer-raw-fields
created_at: '2026-05-19T06:35:02Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/domain/entities/uniprot.py
summary: Added missing UniProt raw/canonical structured payload fields to UniprotTarget
  and refreshed the transformer snapshot to match current output; verified targeted
  snapshot and content-hash contract tests.
---

# Episodic summary

## Task

- Title: Fix UniProt transformer raw structured payload fields

## Outcome

- Added missing UniProt raw/canonical structured payload fields to UniprotTarget and refreshed the transformer snapshot to match current output; verified targeted snapshot and content-hash contract tests.

## Lessons learned

- Replace with durable follow-up if needed
