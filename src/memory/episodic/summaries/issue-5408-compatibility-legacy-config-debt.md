---
id: issue-5408-compatibility-legacy-config-debt
title: 'Close #5408 compatibility legacy config debt'
task_id: issue-5408-compatibility-legacy-config-debt
created_at: '2026-06-18T18:03:08Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_config_taxonomy_review.py
- reports/quality/config-compatibility-legacy-taxonomy-review.json
summary: Added exact-key freeze for config compatibility_legacy taxonomy review. The
  reviewed artifact now records every live compatibility_legacy key by family, and
  the architecture guard compares live taxonomy keys with the reviewed set so new
  or rotated legacy config/schema deviations cannot hide behind unchanged aggregate
  counts. Debt budgets were not increased; debt_scorecard and config-discrepancy baseline
  were unchanged. Validated ruff, generate-config-matrix --check, taxonomy/ratchet
  architecture tests, compatibility registry tests, and validate-configs.
---

# Episodic summary

## Task

- Title: Close #5408 compatibility legacy config debt

## Outcome

- Added exact-key freeze for config compatibility_legacy taxonomy review. The reviewed artifact now records every live compatibility_legacy key by family, and the architecture guard compares live taxonomy keys with the reviewed set so new or rotated legacy config/schema deviations cannot hide behind unchanged aggregate counts. Debt budgets were not increased; debt_scorecard and config-discrepancy baseline were unchanged. Validated ruff, generate-config-matrix --check, taxonomy/ratchet architecture tests, compatibility registry tests, and validate-configs.

## Lessons learned

- Replace with durable follow-up if needed
