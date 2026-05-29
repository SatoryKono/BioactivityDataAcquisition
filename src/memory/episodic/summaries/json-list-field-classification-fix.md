---
id: json-list-field-classification-fix
title: Classify chembl target xref list-like fields
task_id: json-list-field-classification-fix
created_at: '2026-05-29T17:06:17Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/domain/normalization/profiles/chembl_target.py
summary: Added JSON/list-like explicit wording in chembl target profile special rules
  for target_xref_pdb_ids and target_xref_reactome_ids, then re-ran the unit guard
  for JSON/list-like field classification.
---

# Episodic summary

## Task

- Title: Classify chembl target xref list-like fields

## Outcome

- Added JSON/list-like explicit wording in chembl target profile special rules for target_xref_pdb_ids and target_xref_reactome_ids, then re-ran the unit guard for JSON/list-like field classification.

## Lessons learned

- Replace with durable follow-up if needed
