---
id: csv-export-compat-fix-20260603
title: Fix CsvExporter export_table compatibility
task_id: csv-export-compat-fix-20260603
created_at: '2026-06-03T07:29:32Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/infrastructure/export/csv_exporter.py
- tests/integration/infrastructure/export/test_csv_dq_export.py
- reports/quality/module-coverage-inventory.json
summary: Added a backward-compatible CsvExporter.export_table sync wrapper, aligned
  export integration tests with current CSV quoting and BronzeDQReport contracts,
  and refreshed module coverage inventory hash.
---

# Episodic summary

## Task

- Title: Fix CsvExporter export_table compatibility

## Outcome

- Added a backward-compatible CsvExporter.export_table sync wrapper, aligned export integration tests with current CSV quoting and BronzeDQReport contracts, and refreshed module coverage inventory hash.

## Lessons learned

- Replace with durable follow-up if needed
