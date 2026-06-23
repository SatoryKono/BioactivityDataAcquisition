---
id: fix-ownership-map-non-gold-reasons
title: Fix pipeline ownership map non-Gold exclusion reasons
task_id: fix-ownership-map-non-gold-reasons
created_at: '2026-06-23T07:40:46Z'
ttl_days: 14
confidence: episodic
source_refs:
- scripts/engineering/qa/report_pipeline_config_contract_ownership.py
summary: 'Fixed pipeline-config-contract ownership map integrity failure by making
  the ownership-map generator emit gold_runtime_disabled for non-Gold rows when sink/gold
  is absent or disabled. Regenerated reports/quality/pipeline-config-contract-ownership-map
  JSON/MD. Validation passed: ownership map generator --check, ownership map architecture
  tests, config validation, required-fields check, and ruff on the generator.'
---

# Episodic summary

## Task

- Title: Fix pipeline ownership map non-Gold exclusion reasons

## Outcome

- Fixed pipeline-config-contract ownership map integrity failure by making the ownership-map generator emit gold_runtime_disabled for non-Gold rows when sink/gold is absent or disabled. Regenerated reports/quality/pipeline-config-contract-ownership-map JSON/MD. Validation passed: ownership map generator --check, ownership map architecture tests, config validation, required-fields check, and ruff on the generator.

## Lessons learned

- Replace with durable follow-up if needed
