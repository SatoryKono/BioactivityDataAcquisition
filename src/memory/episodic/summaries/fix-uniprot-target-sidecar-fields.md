---
id: fix-uniprot-target-sidecar-fields
title: Fix UniprotTarget sidecar field drift
task_id: fix-uniprot-target-sidecar-fields
created_at: '2026-05-19T06:32:21Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/domain/entities/uniprot.py
summary: Aligned UniprotTarget with the active UniProt Silver schema by adding missing
  feature sidecar fields so transformer business payloads are accepted again.
---

# Episodic summary

## Task

- Title: Fix UniprotTarget sidecar field drift

## Outcome

- Aligned UniprotTarget with the active UniProt Silver schema by adding missing feature sidecar fields so transformer business payloads are accepted again.

## Lessons learned

- Replace with durable follow-up if needed
