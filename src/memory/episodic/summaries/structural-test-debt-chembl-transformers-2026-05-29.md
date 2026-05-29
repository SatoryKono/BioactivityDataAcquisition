---
id: structural-test-debt-chembl-transformers-2026-05-29
title: Reduce oversized ChEMBL transformer test module
task_id: structural-test-debt-chembl-transformers-2026-05-29
created_at: '2026-05-29T15:27:07Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Split PublicationTerm transformer coverage out of test_chembl_transformers.py
  into a dedicated publication-term test module, reducing the original file from 2036
  to 1485 LOC while preserving targeted transformer and structural debt test coverage.
---

# Episodic summary

## Task

- Title: Reduce oversized ChEMBL transformer test module

## Outcome

- Split PublicationTerm transformer coverage out of test_chembl_transformers.py into a dedicated publication-term test module, reducing the original file from 2036 to 1485 LOC while preserving targeted transformer and structural debt test coverage.

## Lessons learned

- Replace with durable follow-up if needed
