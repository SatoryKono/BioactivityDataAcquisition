---
id: debug-e2e-timeout-20260622
title: Debug e2e timeout in sequential chembl/uniprot run
task_id: debug-e2e-timeout-20260622
created_at: '2026-06-22T12:51:55Z'
ttl_days: 14
confidence: episodic
source_refs:
- AGENTS.md
summary: 'Root cause: shared Delta read helper preferred DeltaTable.to_pyarrow_dataset(),
  which imports pyarrow.dataset and can hang on Windows mixed-checkout E2E lanes.
  Fixed by disabling dataset-scanner path on win32 and falling back to to_pyarrow_table;
  added unit coverage for both paths and refreshed module coverage inventory hash.'
---

# Episodic summary

## Task

- Title: Debug e2e timeout in sequential chembl/uniprot run

## Outcome

- Root cause: shared Delta read helper preferred DeltaTable.to_pyarrow_dataset(), which imports pyarrow.dataset and can hang on Windows mixed-checkout E2E lanes. Fixed by disabling dataset-scanner path on win32 and falling back to to_pyarrow_table; added unit coverage for both paths and refreshed module coverage inventory hash.

## Lessons learned

- Replace with durable follow-up if needed
