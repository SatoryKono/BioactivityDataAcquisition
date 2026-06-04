---
id: fix-csv-exporter-atomic-backup-locked-target-20260604
title: Fix CsvExporter atomic backup for locked target
task_id: fix-csv-exporter-atomic-backup-locked-target-20260604
created_at: '2026-06-04T14:32:56Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/infrastructure/export/test_csv_exporter.py::TestCsvExporterInternals::test_atomic_csv_write_locked_target_uses_backup
summary: Made the POSIX/replace locked-target CsvExporter unit test platform-deterministic
  by monkeypatching csv_exporter_io_ops.os.name to posix before patching Path.replace.
  This preserves the separate Windows copy-publish locked-target coverage and fixes
  the Windows failure where Path.replace was intentionally not called. Targeted test
  and full CSV exporter unit file pass.
---

# Episodic summary

## Task

- Title: Fix CsvExporter atomic backup for locked target

## Outcome

- Made the POSIX/replace locked-target CsvExporter unit test platform-deterministic by monkeypatching csv_exporter_io_ops.os.name to posix before patching Path.replace. This preserves the separate Windows copy-publish locked-target coverage and fixes the Windows failure where Path.replace was intentionally not called. Targeted test and full CSV exporter unit file pass.

## Lessons learned

- Replace with durable follow-up if needed
