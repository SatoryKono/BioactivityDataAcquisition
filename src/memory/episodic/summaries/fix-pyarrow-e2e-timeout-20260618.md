---
id: fix-pyarrow-e2e-timeout-20260618
title: Fix pyarrow parquet import timeout in Windows E2E
task_id: fix-pyarrow-e2e-timeout-20260618
created_at: '2026-06-18T07:28:57Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/e2e/conftest.py
summary: Replaced E2E direct pyarrow.parquet reads with shared Delta scanner helper
  and added delegation regression test.
---

# Episodic summary

## Task

- Title: Fix pyarrow parquet import timeout in Windows E2E

## Outcome

- Replaced E2E direct pyarrow.parquet reads with shared Delta scanner helper and added delegation regression test.

## Lessons learned

- Replace with durable follow-up if needed
