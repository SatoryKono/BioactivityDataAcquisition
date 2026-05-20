---
id: chembl-publication-single-value-fields-2026-05-20
title: Reduce chembl_publication output surface
task_id: chembl-publication-single-value-fields-2026-05-20
created_at: '2026-05-20T05:56:39Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
summary: Reduced chembl_publication silver/gold output by excluding provider-gap and
  derived empty columns; propagated unified data_schema projection into pipeline/domain
  config and writer runtime so layer include_groups/exclude_fields are enforced at
  write/validation time; updated chembl publication unit/e2e/snapshot and config normalization
  tests.
---

# Episodic summary

## Task

- Title: Reduce chembl_publication output surface

## Outcome

- Reduced chembl_publication silver/gold output by excluding provider-gap and derived empty columns; propagated unified data_schema projection into pipeline/domain config and writer runtime so layer include_groups/exclude_fields are enforced at write/validation time; updated chembl publication unit/e2e/snapshot and config normalization tests.

## Lessons learned

- Replace with durable follow-up if needed
