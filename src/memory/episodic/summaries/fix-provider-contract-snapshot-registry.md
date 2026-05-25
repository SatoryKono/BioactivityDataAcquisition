---
id: fix-provider-contract-snapshot-registry
title: Fix provider contract snapshot registry regression
task_id: fix-provider-contract-snapshot-registry
created_at: '2026-05-25T14:00:32Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/contract/test_provider_contract_snapshot_registry.py
summary: Restored snapshot-registry compatibility hooks in live provider canary modules
  without reintroducing replay assertions into the live lane.
---

# Episodic summary

## Task

- Title: Fix provider contract snapshot registry regression

## Outcome

- Restored snapshot-registry compatibility hooks in live provider canary modules without reintroducing replay assertions into the live lane.

## Lessons learned

- Replace with durable follow-up if needed
