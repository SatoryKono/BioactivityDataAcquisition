---
id: fix-silver-gold-filter-parity-schema-regression-20260617
title: Fix silver/gold filter parity schema regression
task_id: fix-silver-gold-filter-parity-schema-regression-20260617
created_at: '2026-06-17T05:19:17Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Verified silver/gold parity report schema still includes contract_ref, contract_version,
  source_profile_id, and source_profile_version; rewrote the committed parity report
  with the canonical CLI and confirmed the committed artifact matches the live builder
  and targeted integration tests.
---

# Episodic summary

## Task

- Title: Fix silver/gold filter parity schema regression

## Outcome

- Verified silver/gold parity report schema still includes contract_ref, contract_version, source_profile_id, and source_profile_version; rewrote the committed parity report with the canonical CLI and confirmed the committed artifact matches the live builder and targeted integration tests.

## Lessons learned

- Replace with durable follow-up if needed
