---
id: fix-diagnostics-loc-limit
title: Fix diagnostics CLI LOC limit
task_id: fix-diagnostics-loc-limit
created_at: '2026-06-17T07:26:39Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_code_metrics.py
summary: Fixed the interfaces LOC guard failure by removing an unused diagnostics
  CLI constant, keeping src/bioetl/interfaces/cli/commands/diagnostics.py at exactly
  420 lines without raising file-size budgets. Verified ruff, formatter check, the
  targeted architecture LOC test, diagnostics unit boundary tests, refreshed module
  coverage inventory, and observed the module coverage source hash guard skip on WSL.
---

# Episodic summary

## Task

- Title: Fix diagnostics CLI LOC limit

## Outcome

- Fixed the interfaces LOC guard failure by removing an unused diagnostics CLI constant, keeping src/bioetl/interfaces/cli/commands/diagnostics.py at exactly 420 lines without raising file-size budgets. Verified ruff, formatter check, the targeted architecture LOC test, diagnostics unit boundary tests, refreshed module coverage inventory, and observed the module coverage source hash guard skip on WSL.

## Lessons learned

- Replace with durable follow-up if needed
