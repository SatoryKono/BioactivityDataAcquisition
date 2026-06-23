---
id: e2e-delta-read-timeout-fix
title: Debug e2e Delta table read timeout after successful chembl target run
task_id: e2e-delta-read-timeout-fix
created_at: '2026-06-23T06:08:46Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/e2e/test_advanced_scenarios_e2e.py
summary: Updated the E2E Delta read helper to bypass DeltaTable Arrow scans on win32
  and read active parquet files from DeltaTable.file_uris(), then added helper regression
  coverage and verified the previously failing sequential chembl/uniprot E2E passes.
---

# Episodic summary

## Task

- Title: Debug e2e Delta table read timeout after successful chembl target run

## Outcome

- Updated the E2E Delta read helper to bypass DeltaTable Arrow scans on win32 and read active parquet files from DeltaTable.file_uris(), then added helper regression coverage and verified the previously failing sequential chembl/uniprot E2E passes.

## Lessons learned

- Replace with durable follow-up if needed
