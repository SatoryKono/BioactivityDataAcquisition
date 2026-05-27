---
id: fix-source-module-governance-inventory-20260526
title: Fix source module governance inventory drift
task_id: fix-source-module-governance-inventory-20260526
created_at: '2026-05-26T12:00:53Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/quality/debt_scorecard.yaml
- tests/architecture/test_source_module_governance_inventory.py
- src/bioetl/infrastructure/control_plane/file_run_ledger_store.py
summary: Synced oversized source module inventory for file_run_ledger_store.py from
  stale 471 lines to current 490 lines; targeted architecture inventory test passes.
  Broader code metrics check still reports pre-existing size/function-length debt
  in _health_server_routing_support.py.
---

# Episodic summary

## Task

- Title: Fix source module governance inventory drift

## Outcome

- Synced oversized source module inventory for file_run_ledger_store.py from stale 471 lines to current 490 lines; targeted architecture inventory test passes. Broader code metrics check still reports pre-existing size/function-length debt in _health_server_routing_support.py.

## Lessons learned

- Source module governance inventory can drift even when source size is already
  present in HEAD; verify `git show HEAD:<path> | wc -l` before treating it as
  new local growth.
