---
id: fix-compatibility-importer-census-drift
title: Fix compatibility importer census drift
task_id: fix-compatibility-importer-census-drift
created_at: '2026-06-04T17:24:14Z'
ttl_days: 14
confidence: episodic
source_refs:
- reports/quality/compatibility-importer-census.json
summary: 'Regenerated compatibility importer census JSON/Markdown after new composite
  config test importers raised retained entrypoint test_importer_count from 35 to
  39 without changing src importer counts or budgets. Validation passed: report-compatibility-importer-census
  --check and targeted architecture sync test.'
---

# Episodic summary

## Task

- Title: Fix compatibility importer census drift

## Outcome

- Regenerated compatibility importer census JSON/Markdown after new composite config test importers raised retained entrypoint test_importer_count from 35 to 39 without changing src importer counts or budgets. Validation passed: report-compatibility-importer-census --check and targeted architecture sync test.

## Lessons learned

- Replace with durable follow-up if needed
