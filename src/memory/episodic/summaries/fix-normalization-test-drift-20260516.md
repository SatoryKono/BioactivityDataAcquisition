---
id: fix-normalization-test-drift-20260516
title: Fix normalization test drift
task_id: fix-normalization-test-drift-20260516
created_at: '2026-05-16T09:15:28Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Updated neo4j_memory_sync expectations for chembl_assay_parameters fallback_business_field_count
  and fallback_field_count to 3, and synchronized pipeline normalization matrix tests
  to current activity/assay/assay_parameters/target field names. Verified targeted
  script tests and statement-level normalization evidence pass; snapshot-heavy neo4j
  topology test remains expensive.
---

# Episodic summary

## Task

- Title: Fix normalization test drift

## Outcome

- Updated neo4j_memory_sync expectations for chembl_assay_parameters fallback_business_field_count and fallback_field_count to 3, and synchronized pipeline normalization matrix tests to current activity/assay/assay_parameters/target field names. Verified targeted script tests and statement-level normalization evidence pass; snapshot-heavy neo4j topology test remains expensive.

## Lessons learned

- Replace with durable follow-up if needed
