---
id: chembl-contract-timeout-fix-20260604
title: Fix ChEMBL contract test timeout
task_id: chembl-contract-timeout-fix-20260604
created_at: '2026-06-04T12:47:27Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/contract/test_chembl_contract.py
summary: Stabilized the ChEMBL live contract tests by removing the extra asyncio timeout
  wrapper, reusing a module-scoped AsyncClient on a module-scoped event loop, and
  improving skip diagnostics so Windows/Python 3.13 live runs exit via pass or skip
  instead of hanging until pytest-timeout.
---

# Episodic summary

## Task

- Title: Fix ChEMBL contract test timeout

## Outcome

- Stabilized the ChEMBL live contract tests by removing the extra asyncio timeout wrapper, reusing a module-scoped AsyncClient on a module-scoped event loop, and improving skip diagnostics so Windows/Python 3.13 live runs exit via pass or skip instead of hanging until pytest-timeout.

## Lessons learned

- Replace with durable follow-up if needed
