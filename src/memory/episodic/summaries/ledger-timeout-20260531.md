---
id: ledger-timeout-20260531
title: Debug ledger fsync timeout on Windows replay test
task_id: ledger-timeout-20260531
created_at: '2026-05-31T13:02:19Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/infrastructure/control_plane/file_run_ledger_store.py
summary: Relaxed Windows test-mode control-plane fsync for run-ledger writes, added
  replay_ready regression coverage, reran the idempotency gate successfully, and refreshed
  only module-coverage source_tree_sha256.
---

# Episodic summary

## Task

- Title: Debug ledger fsync timeout on Windows replay test

## Outcome

- Relaxed Windows test-mode control-plane fsync for run-ledger writes, added replay_ready regression coverage, reran the idempotency gate successfully, and refreshed only module-coverage source_tree_sha256.

## Lessons learned

- Replace with durable follow-up if needed
