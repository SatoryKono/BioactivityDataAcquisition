---
id: fix-storage-bootstrap-import-20260521
title: Fix storage bootstrap import regression
task_id: fix-storage-bootstrap-import-20260521
created_at: '2026-05-21T12:32:33Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Updated composition bootstrap storage to import load_contract_registry_entries
  from the canonical contract_registry_loader instead of contract_policy_validation.
  Verified py_compile, direct storage module import, pytest collect-only for test_storage_bootstrap,
  and passing tests/unit/scripts/test_validate_contract_registry.py.
---

# Episodic summary

## Task

- Title: Fix storage bootstrap import regression

## Outcome

- Updated composition bootstrap storage to import load_contract_registry_entries from the canonical contract_registry_loader instead of contract_policy_validation. Verified py_compile, direct storage module import, pytest collect-only for test_storage_bootstrap, and passing tests/unit/scripts/test_validate_contract_registry.py.

## Lessons learned

- Replace with durable follow-up if needed
