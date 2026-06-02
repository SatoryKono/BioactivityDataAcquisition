---
id: debug-export-column-tests-20260602
title: Add tests for failed_field/value/constraint debug export columns
task_id: debug-export-column-tests-20260602
created_at: '2026-06-02T17:00:47Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Added debug-export unit coverage asserting failed_field, failed_value, and
  expected_constraint are populated for semantic gold_rejected, structured silver_rejected,
  and structured silver_quarantine rows. Extended debug export service/collector to
  accept structured details_payload for filtered-out and data-quality failure paths
  so the tests exercise public runtime surfaces.
---

# Episodic summary

## Task

- Title: Add tests for failed_field/value/constraint debug export columns

## Outcome

- Added debug-export unit coverage asserting failed_field, failed_value, and expected_constraint are populated for semantic gold_rejected, structured silver_rejected, and structured silver_quarantine rows. Extended debug export service/collector to accept structured details_payload for filtered-out and data-quality failure paths so the tests exercise public runtime surfaces.

## Lessons learned

- Replace with durable follow-up if needed
