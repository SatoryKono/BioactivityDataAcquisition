---
id: gold-excluded-accounting
title: track-gold-excluded-by-contract
task_id: gold-excluded-accounting
created_at: '2026-05-16T12:45:10Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Added explicit Gold exclusion accounting when should_write_gold rejects a
  valid Silver record. RecordTransformOutcome/TransformedRecord/TransformResult/TransformAggregationState
  now carry gold_excluded_by_contract signal and count. BatchProcessingSupportService
  now emits stage=gold,outcome=excluded_by_contract via track_stage_records so Prometheus
  recording rule bioetl_processed_records_gold_excluded_by_contract_current can observe
  non-zero values. Added unit regressions for batch aggregation, stream aggregation,
  transform_single/transform_stream semantics, and support-service metric emission.
  Verified with py_compile, ruff check, git diff --check, and direct runtime verification
  script; targeted pytest bundle hung silently in this exec environment.
---

# Episodic summary

## Task

- Title: track-gold-excluded-by-contract

## Outcome

- Added explicit Gold exclusion accounting when should_write_gold rejects a valid Silver record. RecordTransformOutcome/TransformedRecord/TransformResult/TransformAggregationState now carry gold_excluded_by_contract signal and count. BatchProcessingSupportService now emits stage=gold,outcome=excluded_by_contract via track_stage_records so Prometheus recording rule bioetl_processed_records_gold_excluded_by_contract_current can observe non-zero values. Added unit regressions for batch aggregation, stream aggregation, transform_single/transform_stream semantics, and support-service metric emission. Verified with py_compile, ruff check, git diff --check, and direct runtime verification script; targeted pytest bundle hung silently in this exec environment.

## Lessons learned

- Replace with durable follow-up if needed
