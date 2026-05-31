---
id: fix-target-xref-json-list-classification
title: Fix target xref JSON list inventory classification
task_id: fix-target-xref-json-list-classification
created_at: '2026-05-31T14:45:29Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
summary: Fixed normalization JSON/list inventory guard to classify explicit pipe-delimited/list-like
  fields without requiring JSON semantics. This resolves target_xref_hgnc_ids and
  target_xref_uniprot_ids while preserving them as ordinary string fields outside
  JSON_STRING_FIELDS and set-like hashing. Validated failing test, chembl_target profile
  tests, and ruff on the changed test.
---

# Episodic summary

## Task

- Title: Fix target xref JSON list inventory classification

## Outcome

- Fixed normalization JSON/list inventory guard to classify explicit pipe-delimited/list-like fields without requiring JSON semantics. This resolves target_xref_hgnc_ids and target_xref_uniprot_ids while preserving them as ordinary string fields outside JSON_STRING_FIELDS and set-like hashing. Validated failing test, chembl_target profile tests, and ruff on the changed test.

## Lessons learned

- Replace with durable follow-up if needed
