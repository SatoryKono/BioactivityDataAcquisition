---
id: fix-silver-gold-filter-parity-drift-20260617
title: Fix Silver Gold filter parity golden drift
task_id: fix-silver-gold-filter-parity-drift-20260617
created_at: '2026-06-17T08:34:03Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/integration/ci/test_silver_gold_filter_parity.py
- scripts/data_quality/run_silver_gold_filter_parity.py
- reports/quality/silver-gold-filter-parity-report.json
summary: Investigated reported Silver/Gold parity golden drift where generated scenarios
  lacked contract_ref, contract_version, source_profile_id, and source_profile_version.
  Current worktree generator scripts/data_quality/run_silver_gold_filter_parity.py
  already emits those fields from cleaned identity anchors, reports/quality/silver-gold-filter-parity-report.json
  is current, and tests/integration/ci/test_silver_gold_filter_parity.py passes locally
  with 7 tests. No source edit was required for this surface.
---

# Episodic summary

## Task

- Title: Fix Silver Gold filter parity golden drift

## Outcome

- Investigated reported Silver/Gold parity golden drift where generated scenarios lacked contract_ref, contract_version, source_profile_id, and source_profile_version. Current worktree generator scripts/data_quality/run_silver_gold_filter_parity.py already emits those fields from cleaned identity anchors, reports/quality/silver-gold-filter-parity-report.json is current, and tests/integration/ci/test_silver_gold_filter_parity.py passes locally with 7 tests. No source edit was required for this surface.

## Lessons learned

- Replace with durable follow-up if needed
