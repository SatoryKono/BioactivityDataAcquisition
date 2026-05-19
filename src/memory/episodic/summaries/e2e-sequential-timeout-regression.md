---
id: e2e-sequential-timeout-regression
title: Debug sequential E2E timeout after ChEMBL target run
task_id: e2e-sequential-timeout-regression
created_at: '2026-05-19T11:16:55Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/bootstrap/runtime/normalization_policy_init.py
- src/bioetl/composition/bootstrap/runtime/classification_init.py
- tests/unit/composition/bootstrap/runtime/test_runtime_data_init.py
- tests/e2e/test_advanced_scenarios_e2e.py
summary: Added process-local caching for bootstrap config-backed ChEMBL policy and
  publication classification loaders to avoid repeated filesystem scans during sequential
  pipeline bootstraps; validated with runtime bootstrap unit tests and sequential/matrix
  E2E.
---

# Episodic summary

## Task

- Title: Debug sequential E2E timeout after ChEMBL target run

## Outcome

- Added process-local caching for bootstrap config-backed ChEMBL policy and publication classification loaders to avoid repeated filesystem scans during sequential pipeline bootstraps; validated with runtime bootstrap unit tests and sequential/matrix E2E.

## Lessons learned

- Replace with durable follow-up if needed
