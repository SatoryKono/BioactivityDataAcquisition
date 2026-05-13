---
id: fix-chembl-normalization-regressions-20260513
title: Fix ChEMBL normalization regressions and refresh reproducibility fixtures
task_id: fix-chembl-normalization-regressions-20260513
created_at: '2026-05-13T16:00:14Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/domain/normalization/profiles/_standard_profile_rule_components.py
summary: Fixed record-aware null handling for normalization rules, seeded ChEMBL activity
  ontology companion fields so derived IRIs/statuses materialize, aligned stale ChEMBL
  tests with current gold-filter and publication-taxonomy contracts, and refreshed
  reproducibility golden fixtures for normalization profile metadata.
---

# Episodic summary

## Task

- Title: Fix ChEMBL normalization regressions and refresh reproducibility fixtures

## Outcome

- Fixed record-aware null handling for normalization rules, seeded ChEMBL activity ontology companion fields so derived IRIs/statuses materialize, aligned stale ChEMBL tests with current gold-filter and publication-taxonomy contracts, and refreshed reproducibility golden fixtures for normalization profile metadata.

## Lessons learned

- Replace with durable follow-up if needed
