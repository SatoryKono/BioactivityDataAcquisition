---
id: fix-source-module-governance-inventory-20260526
title: Fix source module governance inventory drift
task_id: fix-source-module-governance-inventory-20260526
created_at: '2026-05-26T11:51:21Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/quality/debt_scorecard.yaml
- tests/architecture/test_source_module_governance_inventory.py
- src/bioetl/infrastructure/control_plane/file_run_ledger_store.py
summary: Active task session context.
query: tests/architecture/test_source_module_governance_inventory.py oversized source
  module inventory 490 471
---

# Session note

## Task

- Title: Fix source module governance inventory drift
- Retrieval query: tests/architecture/test_source_module_governance_inventory.py oversized source module inventory 490 471

## Retrieved context

- Catalog hits: 0
- RAG hits: 0
- Timeline hits: 0

## Working notes

- `file_run_ledger_store.py` is 490 lines in HEAD/current worktree while
  `debt_scorecard.yaml` still recorded 471.
- Updated only the oversized source module inventory line count; the tracked
  module remains below `max_tracked_lines: 500`.
