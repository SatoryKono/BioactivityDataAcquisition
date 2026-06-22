---
id: cfg-hash-include-invariant
title: Fix runtime config primary key/hash policy invariant
task_id: cfg-hash-include-invariant
created_at: '2026-06-22T16:13:18Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_config_ci_invariants.py
summary: Root hash_policy now feeds runtime-effective contract hash selectors; legacy
  contracts.hash_include/hash_exclude shims are empty in entity configs; config discrepancy
  artifacts regenerated without inflating ratchet budgets.
---

# Episodic summary

## Task

- Title: Fix runtime config primary key/hash policy invariant

## Outcome

- Root hash_policy now feeds runtime-effective contract hash selectors; legacy contracts.hash_include/hash_exclude shims are empty in entity configs; config discrepancy artifacts regenerated without inflating ratchet budgets.

## Lessons learned

- Replace with durable follow-up if needed
