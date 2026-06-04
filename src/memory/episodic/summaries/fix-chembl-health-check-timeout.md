---
id: fix-chembl-health-check-timeout
title: Fix ChemblAdapter health_check timeout
task_id: fix-chembl-health-check-timeout
created_at: '2026-06-04T12:18:34Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/infrastructure/adapters/chembl/health.py
- tests/unit/infrastructure/adapters/chembl/test_chembl_client.py
- reports/quality/module-coverage-inventory.json
summary: Added a provider-local 5s timeout around the ChEMBL /status health probe,
  classified timeout/cancelled probes as DEGRADED, and added unit coverage for a stuck
  get_once call. Targeted ChEMBL unit and VCR integration health-check tests passed.
  Module coverage inventory hash guard was attempted but remained unstable because
  parallel tasks were modifying src/bioetl and reports/quality/module-coverage-inventory.json
  concurrently.
---

# Episodic summary

## Task

- Title: Fix ChemblAdapter health_check timeout

## Outcome

- Added a provider-local 5s timeout around the ChEMBL /status health probe, classified timeout/cancelled probes as DEGRADED, and added unit coverage for a stuck get_once call. Targeted ChEMBL unit and VCR integration health-check tests passed. Module coverage inventory hash guard was attempted but remained unstable because parallel tasks were modifying src/bioetl and reports/quality/module-coverage-inventory.json concurrently.

## Lessons learned

- Replace with durable follow-up if needed
