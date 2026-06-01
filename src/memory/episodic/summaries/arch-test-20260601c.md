---
id: arch-test-20260601c
title: Fix ChemBL target profile hash drift in contract_registry and re-run integration
  test
task_id: ARCH-TEST-20260601C
created_at: '2026-06-01T17:34:40Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Updated chembl.target normalization_profile_hash in configs/base/contract_registry.yaml
  to match live profile identity hash; targeted integration check now passes.
---

# Episodic summary

## Task

- Title: Fix ChemBL target profile hash drift in contract_registry and re-run integration test

## Outcome

- Updated chembl.target normalization_profile_hash in configs/base/contract_registry.yaml to match live profile identity hash; targeted integration check now passes.

## Lessons learned

- Replace with durable follow-up if needed
