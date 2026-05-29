---
id: chembl-target-silver-filter-coverage-2026-05-29
title: Fix ChEMBL target silver filter coverage invariant
task_id: chembl-target-silver-filter-coverage-2026-05-29
created_at: '2026-05-29T15:31:07Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Synchronized configs/entities/chembl/target.yaml silver_filters.required_fields
  with the existing not_null/required quality surface by adding the derived synonym
  and target-xref fields required by INV-CFG-007. Required-field checker and config
  CI invariants now pass.
---

# Episodic summary

## Task

- Title: Fix ChEMBL target silver filter coverage invariant

## Outcome

- Synchronized configs/entities/chembl/target.yaml silver_filters.required_fields with the existing not_null/required quality surface by adding the derived synonym and target-xref fields required by INV-CFG-007. Required-field checker and config CI invariants now pass.

## Lessons learned

- Replace with durable follow-up if needed
