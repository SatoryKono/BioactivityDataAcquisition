---
id: run-gap-cd910d47
title: investigate-missing-93-gold-records
task_id: run-gap-cd910d47
created_at: '2026-05-16T12:29:39Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: 'For run cd910d47-7dcc-4a5a-b4e4-4e09ea4dc8af (chembl_activity), Bronze=10000,
  Silver=9102, Gold=9009. Quarantine fully explains Bronze->Silver loss: 851 FILTERED_OUT_SILVER
  + 47 INVALID_DATA = 898. The remaining 93 are present in Silver and absent in Gold
  by activity_id. Effective config artifact effective-config-fb7e13c7ac2dfecb.json
  shows inherited gold_filters.ranges.pchembl_value min=3 max=10 via silver_filter_migration
  auto-promotion. BaseTransformer.should_write_gold() delegates to GoldFilterConfig.should_include(),
  which evaluates range filters. All 93 missing Silver rows have pchembl_value > 10
  (min 10.03, max 11.00), so they were intentionally excluded from Gold by policy,
  not lost.'
---

# Episodic summary

## Task

- Title: investigate-missing-93-gold-records

## Outcome

- For run cd910d47-7dcc-4a5a-b4e4-4e09ea4dc8af (chembl_activity), Bronze=10000, Silver=9102, Gold=9009. Quarantine fully explains Bronze->Silver loss: 851 FILTERED_OUT_SILVER + 47 INVALID_DATA = 898. The remaining 93 are present in Silver and absent in Gold by activity_id. Effective config artifact effective-config-fb7e13c7ac2dfecb.json shows inherited gold_filters.ranges.pchembl_value min=3 max=10 via silver_filter_migration auto-promotion. BaseTransformer.should_write_gold() delegates to GoldFilterConfig.should_include(), which evaluates range filters. All 93 missing Silver rows have pchembl_value > 10 (min 10.03, max 11.00), so they were intentionally excluded from Gold by policy, not lost.

## Lessons learned

- Replace with durable follow-up if needed
