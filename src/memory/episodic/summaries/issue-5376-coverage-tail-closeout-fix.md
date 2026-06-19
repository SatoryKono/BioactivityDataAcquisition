---
id: issue-5376-coverage-tail-closeout-fix
title: Fix Bronze batch path normalization regression
task_id: issue-5376-coverage-tail-closeout-fix
created_at: '2026-06-19T14:43:34Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/infrastructure/storage/bronze/read_cleanup_mixin.py
summary: Normalized Bronze list_batches output to POSIX relative paths so Windows
  separators no longer leak into medallion regression envelopes; refreshed module
  coverage inventory and architecture quality scorecard after the storage source change.
---

# Episodic summary

## Task

- Title: Fix Bronze batch path normalization regression

## Outcome

- Normalized Bronze list_batches output to POSIX relative paths so Windows separators no longer leak into medallion regression envelopes; refreshed module coverage inventory and architecture quality scorecard after the storage source change.

## Lessons learned

- Replace with durable follow-up if needed
