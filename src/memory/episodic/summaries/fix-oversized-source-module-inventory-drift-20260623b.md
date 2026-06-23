---
id: fix-oversized-source-module-inventory-drift-20260623b
title: Fix oversized source module inventory drift after ruff
task_id: fix-oversized-source-module-inventory-drift-20260623b
created_at: '2026-06-23T06:09:17Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/quality/debt_scorecard.yaml
summary: 'Synchronized configs/quality/debt_scorecard.yaml oversized_source_module_inventory
  for src/bioetl/interfaces/cli/commands/domains/health/server_integration.py from
  353 to the current measured 355 lines after import-order formatting. max_tracked_lines
  remains 500 and no debt budgets were increased. Validation: test_source_module_governance_inventory.py
  passed, test_scorecard_baseline_matches_registry passed, direct top_modules line-count
  check passed, YAML parse passed.'
---

# Episodic summary

## Task

- Title: Fix oversized source module inventory drift after ruff

## Outcome

- Synchronized configs/quality/debt_scorecard.yaml oversized_source_module_inventory for src/bioetl/interfaces/cli/commands/domains/health/server_integration.py from 353 to the current measured 355 lines after import-order formatting. max_tracked_lines remains 500 and no debt budgets were increased. Validation: test_source_module_governance_inventory.py passed, test_scorecard_baseline_matches_registry passed, direct top_modules line-count check passed, YAML parse passed.

## Lessons learned

- Replace with durable follow-up if needed
