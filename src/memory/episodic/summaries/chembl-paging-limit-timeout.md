---
id: chembl-paging-limit-timeout
title: Fix ChEMBL oversized pagination timeout
task_id: chembl-paging-limit-timeout
created_at: '2026-06-03T10:28:18Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/integration/adapters/test_chembl_paging_resilience.py
summary: Converted oversized ChEMBL pagination limit test from live/VCR-backed limit=1_000_000
  fetch to deterministic finite-page fake client. Removed unused imports and made
  config assertion tests consume constructed adapters. Targeted pagination test, whole
  file, ruff check, and test-governance collector pass.
---

# Episodic summary

## Task

- Title: Fix ChEMBL oversized pagination timeout

## Outcome

- Converted oversized ChEMBL pagination limit test from live/VCR-backed limit=1_000_000 fetch to deterministic finite-page fake client. Removed unused imports and made config assertion tests consume constructed adapters. Targeted pagination test, whole file, ruff check, and test-governance collector pass.

## Lessons learned

- Replace with durable follow-up if needed
