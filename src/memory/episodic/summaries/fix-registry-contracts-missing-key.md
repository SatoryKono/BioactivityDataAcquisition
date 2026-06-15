---
id: fix-registry-contracts-missing-key
title: Fix datasource creator missing-key contract
task_id: fix_registry_contracts_missing_key
created_at: '2026-06-15T17:45:18Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Restored get_data_source_creator() missing-provider KeyError contract without
  reintroducing eager provider bootstrap by validating unknown default providers against
  config-backed names plus sanctioned registry-only aliases; refreshed module coverage
  inventory and architecture scorecard; targeted Linux and Windows tests passed.
---

# Episodic summary

## Task

- Title: Fix datasource creator missing-key contract

## Outcome

- Restored get_data_source_creator() missing-provider KeyError contract without reintroducing eager provider bootstrap by validating unknown default providers against config-backed names plus sanctioned registry-only aliases; refreshed module coverage inventory and architecture scorecard; targeted Linux and Windows tests passed.

## Lessons learned

- Replace with durable follow-up if needed
