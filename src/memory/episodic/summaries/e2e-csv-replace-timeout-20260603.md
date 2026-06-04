---
id: e2e-csv-replace-timeout-20260603
title: Fix E2E CSV atomic replace timeout
task_id: e2e-csv-replace-timeout-20260603
created_at: '2026-06-03T18:32:05Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/infrastructure/export/csv_exporter_io_ops.py
summary: Fixed Windows/GDrive CSV sidecar timeout by avoiding os.replace on Windows
  CSV publish paths; added unit regression tests; verified targeted CSV suites and
  Windows E2E sequential ChEMBL+UniProt test.
---

# Episodic summary

## Task

- Title: Fix E2E CSV atomic replace timeout

## Outcome

- Fixed Windows/GDrive CSV sidecar timeout by avoiding os.replace on Windows CSV publish paths; added unit regression tests; verified targeted CSV suites and Windows E2E sequential ChEMBL+UniProt test.

## Lessons learned

- Replace with durable follow-up if needed
