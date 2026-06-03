---
id: test-governance-audit-drift-20260603
title: Fix test governance audit drift without changing budgets
task_id: test-governance-audit-drift-20260603
created_at: '2026-06-03T06:52:37Z'
ttl_days: 14
confidence: episodic
source_refs:
- reports/quality/test-governance-current.json
summary: Eliminated duplicate test-name governance debt by renaming residual generic
  test function names across affected unit modules, kept committed budgets unchanged,
  updated configs/quality/test_governance_audit.yaml assertless triage metadata to
  intentional_no_exception_contract=482, and regenerated reports/quality/test-governance-current.json
  plus reports/quality/test-duplicate-name-inventory.json from the canonical collector.
---

# Episodic summary

## Task

- Title: Fix test governance audit drift without changing budgets

## Outcome

- Eliminated duplicate test-name governance debt by renaming residual generic test function names across affected unit modules, kept committed budgets unchanged, updated configs/quality/test_governance_audit.yaml assertless triage metadata to intentional_no_exception_contract=482, and regenerated reports/quality/test-governance-current.json plus reports/quality/test-duplicate-name-inventory.json from the canonical collector.

## Lessons learned

- Replace with durable follow-up if needed
