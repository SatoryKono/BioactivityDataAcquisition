---
id: fix-csv-exporter-atomic-backup-locked-target-20260604
title: Fix CsvExporter atomic backup for locked target
task_id: fix-csv-exporter-atomic-backup-locked-target-20260604
created_at: '2026-06-04T14:31:31Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/infrastructure/export/test_csv_exporter.py::TestCsvExporterInternals::test_atomic_csv_write_locked_target_uses_backup
summary: Active task session context.
query: TestCsvExporterInternals test_atomic_csv_write_locked_target_uses_backup atomic
  csv write backup locked target
---

# Session note

## Task

- Title: Fix CsvExporter atomic backup for locked target
- Retrieval query: TestCsvExporterInternals test_atomic_csv_write_locked_target_uses_backup atomic csv write backup locked target

## Retrieved context

- Catalog hits: 0
- RAG hits: 0
- Timeline hits: 0

## Working notes

- Replace with current findings
