---
id: e2e-delta-read-timeout
title: Stabilize E2E Delta assertions after Silver pipeline runs
task_id: e2e-delta-read-timeout
created_at: '2026-05-25T17:22:42Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/e2e/conftest.py
summary: Disabled Silver compaction in E2E and switched E2E Delta assertions from
  DeltaTable.to_pyarrow_table() to reading active parquet files from Delta log URIs.
  This avoids Windows/PyCharm timeout paths while preserving E2E artifact assertions.
---

# Episodic summary

## Task

- Title: Stabilize E2E Delta assertions after Silver pipeline runs

## Outcome

- Disabled Silver compaction in E2E and switched E2E Delta assertions from DeltaTable.to_pyarrow_table() to reading active parquet files from Delta log URIs. This avoids Windows/PyCharm timeout paths while preserving E2E artifact assertions.

## Lessons learned

- Replace with durable follow-up if needed
