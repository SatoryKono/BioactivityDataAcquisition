---
id: control-plane-storage-contract-compat
title: Fix control-plane file store integration contract compatibility
task_id: control-plane-storage-contract-compat
created_at: '2026-06-03T07:45:01Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/domain/control_plane/run_manifest.py
summary: Restored legacy storage-contract construction for RunManifest via deterministic
  InitVar compatibility fields and added pure-domain LedgerEvent import surface at
  bioetl.domain.control_plane.ledger.core_events; refreshed module coverage inventory
  and dependency map, then validated storage and architecture guards.
---

# Episodic summary

## Task

- Title: Fix control-plane file store integration contract compatibility

## Outcome

- Restored legacy storage-contract construction for RunManifest via deterministic InitVar compatibility fields and added pure-domain LedgerEvent import surface at bioetl.domain.control_plane.ledger.core_events; refreshed module coverage inventory and dependency map, then validated storage and architecture guards.

## Lessons learned

- Replace with durable follow-up if needed
