---
id: lineage-fsync-timeout-20260602
title: Fix lineage store fsync timeout
task_id: lineage-fsync-timeout-20260602
created_at: '2026-06-02T19:01:38Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/infrastructure/control_plane/file_lineage_store.py
- src/bioetl/infrastructure/control_plane/_durability.py
- reports/quality/module-coverage-inventory.json
summary: 'RCA: user timeout log came from an older Windows checkout where file_lineage_store
  appended JSONL indexes with direct os.fsync. Current source already routes lineage,
  run-ledger, and workflow-ledger flushes through shared control-plane durability
  policy, skipping fsync only for Windows BIOETL_TEST_MODE while preserving production
  durability. Validated storage/control-plane unit tests, lineage reproducibility
  contract, ruff, format, module coverage check, module coverage architecture guard,
  and private-module import guard. Refreshed module-coverage inventory after concurrent
  source-tree drift stabilized.'
---

# Episodic summary

## Task

- Title: Fix lineage store fsync timeout

## Outcome

- RCA: user timeout log came from an older Windows checkout where file_lineage_store appended JSONL indexes with direct os.fsync. Current source already routes lineage, run-ledger, and workflow-ledger flushes through shared control-plane durability policy, skipping fsync only for Windows BIOETL_TEST_MODE while preserving production durability. Validated storage/control-plane unit tests, lineage reproducibility contract, ruff, format, module coverage check, module coverage architecture guard, and private-module import guard. Refreshed module-coverage inventory after concurrent source-tree drift stabilized.

## Lessons learned

- Replace with durable follow-up if needed
