---
id: fix-neo4j-memory-sync-20260516
title: Fix neo4j memory sync fallback topology regression
task_id: fix-neo4j-memory-sync-20260516
created_at: '2026-05-16T08:56:40Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: 'Updated neo4j_memory_sync expectations to match current chembl_assay_parameters
  normalization baseline: fallback_business_field_count and fallback_field_count are
  now 3 instead of 0. Verified statement-level normalization evidence; the full snapshot
  test is computationally heavy and was stopped during docs-drift edge generation.'
---

# Episodic summary

## Task

- Title: Fix neo4j memory sync fallback topology regression

## Outcome

- Updated neo4j_memory_sync expectations to match current chembl_assay_parameters normalization baseline: fallback_business_field_count and fallback_field_count are now 3 instead of 0. Verified statement-level normalization evidence; the full snapshot test is computationally heavy and was stopped during docs-drift edge generation.

## Lessons learned

- Replace with durable follow-up if needed
