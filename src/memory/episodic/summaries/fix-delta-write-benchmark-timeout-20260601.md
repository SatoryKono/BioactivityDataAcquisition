---
id: fix-delta-write-benchmark-timeout-20260601
title: Fix delta write append benchmark timeout
task_id: fix-delta-write-benchmark-timeout-20260601
created_at: '2026-06-01T05:52:55Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/benchmarks/test_delta_write.py
summary: Adjusted Delta write benchmark-only timeout budgets so cold delta-rs startup
  on Windows filesystems and Windows-backed mounts does not trip the production Silver
  write timeout during throughput tests. Verified ruff and the failing append-small
  benchmark with pytest-benchmark enabled.
---

# Episodic summary

## Task

- Title: Fix delta write append benchmark timeout

## Outcome

- Adjusted Delta write benchmark-only timeout budgets so cold delta-rs startup on Windows filesystems and Windows-backed mounts does not trip the production Silver write timeout during throughput tests. Verified ruff and the failing append-small benchmark with pytest-benchmark enabled.

## Lessons learned

- Replace with durable follow-up if needed
