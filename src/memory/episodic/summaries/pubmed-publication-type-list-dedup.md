---
id: pubmed-publication-type-list-dedup
title: Remove duplicate PubMed publication_type_list field
task_id: pubmed-publication-type-list-dedup
created_at: '2026-05-06T09:34:36Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/application/pipelines/pubmed
summary: Removed duplicate PubMed publication_type_list from emitted records, entity/schema/gold
  contracts, normalization structured-field policies, composite/config field groups,
  snapshots, fixtures, and reference docs. Canonical publication_types remains the
  PubMed structured publication-type field. Validated no remaining publication_type_list
  references in src/tests/configs/relevant docs; PubMed focused transformer/parser/schema/field-group
  tests passed; direct gold/hash checks passed; ruff passed. Silver pipeline schema
  field-name test remains failing for stale multi-provider expectations unrelated
  to publication_type_list.
---

# Episodic summary

## Task

- Title: Remove duplicate PubMed publication_type_list field

## Outcome

- Removed duplicate PubMed publication_type_list from emitted records, entity/schema/gold contracts, normalization structured-field policies, composite/config field groups, snapshots, fixtures, and reference docs. Canonical publication_types remains the PubMed structured publication-type field. Validated no remaining publication_type_list references in src/tests/configs/relevant docs; PubMed focused transformer/parser/schema/field-group tests passed; direct gold/hash checks passed; ruff passed. Silver pipeline schema field-name test remains failing for stale multi-provider expectations unrelated to publication_type_list.

## Lessons learned

- Replace with durable follow-up if needed
