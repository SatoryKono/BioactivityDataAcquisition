---
id: fix-export-reader-import-20260521
title: Fix export reader storage bootstrap import regression
task_id: fix-export-reader-import-20260521
created_at: '2026-05-21T12:36:00Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Confirmed storage bootstrap was still importing load_contract_registry_entries
  from the deprecated contract_policy_validation seam in HEAD. Kept the corrected
  import to contract_registry_loader in src/bioetl/composition/bootstrap/cli/storage.py
  and verified py_compile, collect-only for test_export_reader_version_fallback.py,
  and a passing 2-test pytest run for that file.
---

# Episodic summary

## Task

- Title: Fix export reader storage bootstrap import regression

## Outcome

- Confirmed storage bootstrap was still importing load_contract_registry_entries from the deprecated contract_policy_validation seam in HEAD. Kept the corrected import to contract_registry_loader in src/bioetl/composition/bootstrap/cli/storage.py and verified py_compile, collect-only for test_export_reader_version_fallback.py, and a passing 2-test pytest run for that file.

## Lessons learned

- Replace with durable follow-up if needed
