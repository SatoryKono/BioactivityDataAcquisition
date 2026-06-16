---
id: fix-adr-050-silver-filter-inventory-drift
title: Fix ADR-050 silver filter inventory baseline drift
task_id: fix-adr-050-silver-filter-inventory-drift
created_at: '2026-06-16T17:42:48Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_silver_filter_boundary_inventory.py
summary: Re-ran scripts/data_quality/inventory_silver_filters_migration.py and verified
  docs/filters/inventory-baseline.{csv,json,md} now match generator output. The current
  checkout already has first_line=359 for src/bioetl/interfaces/cli/commands/diagnostics.py
  in the ADR-050 inventory baseline, so no persistent file diff remains. Validated
  tests/architecture/test_silver_filter_boundary_inventory.py::test_inventory_baseline_outputs_match_generator
  and the full tests/architecture/test_silver_filter_boundary_inventory.py file.
---

# Episodic summary

## Task

- Title: Fix ADR-050 silver filter inventory baseline drift

## Outcome

- Re-ran scripts/data_quality/inventory_silver_filters_migration.py and verified docs/filters/inventory-baseline.{csv,json,md} now match generator output. The current checkout already has first_line=359 for src/bioetl/interfaces/cli/commands/diagnostics.py in the ADR-050 inventory baseline, so no persistent file diff remains. Validated tests/architecture/test_silver_filter_boundary_inventory.py::test_inventory_baseline_outputs_match_generator and the full tests/architecture/test_silver_filter_boundary_inventory.py file.

## Lessons learned

- Replace with durable follow-up if needed
