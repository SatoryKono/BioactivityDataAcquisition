---
id: domain-enum-catalog-loc-20260604
title: Reduce _chembl_enum_catalog below LOC limit
task_id: domain-enum-catalog-loc-20260604
created_at: '2026-06-04T07:41:52Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/domain/schemas/_chembl_enum_catalog.py
summary: Split target/publication vocab out of the ChEMBL enum catalog to bring the
  domain module below the file-size limit, preserved public imports, updated source-tree
  hash, and verified targeted architecture/schema tests.
---

# Episodic summary

## Task

- Title: Reduce _chembl_enum_catalog below LOC limit

## Outcome

- Split target/publication vocab out of the ChEMBL enum catalog to bring the domain module below the file-size limit, preserved public imports, updated source-tree hash, and verified targeted architecture/schema tests.

## Lessons learned

- Replace with durable follow-up if needed
