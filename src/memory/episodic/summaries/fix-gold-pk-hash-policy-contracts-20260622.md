---
id: fix-gold-pk-hash-policy-contracts-20260622
title: Fix Gold PK hash policy contract failures
task_id: fix-gold-pk-hash-policy-contracts-20260622
created_at: '2026-06-22T16:10:01Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/contract/test_gold_pk_consistency.py
summary: Fixed order/cache-sensitive Gold PK contract failures by clearing load_pipeline_config
  cache before PK consistency config loads and before per-entity resolved config checks.
  Added a contract regression guard that root hash_policy entity configs keep legacy
  contracts.hash_include/hash_exclude shims empty, preserving hash_policy as the runtime-authoritative
  selector. Validation passed for test_gold_pk_consistency.py, related hash-policy
  integration tests, a contract ordering slice around the failing 66 percent region,
  and ruff. Runtime/config files were not changed.
---

# Episodic summary

## Task

- Title: Fix Gold PK hash policy contract failures

## Outcome

- Fixed order/cache-sensitive Gold PK contract failures by clearing load_pipeline_config cache before PK consistency config loads and before per-entity resolved config checks. Added a contract regression guard that root hash_policy entity configs keep legacy contracts.hash_include/hash_exclude shims empty, preserving hash_policy as the runtime-authoritative selector. Validation passed for test_gold_pk_consistency.py, related hash-policy integration tests, a contract ordering slice around the failing 66 percent region, and ruff. Runtime/config files were not changed.

## Lessons learned

- Replace with durable follow-up if needed
