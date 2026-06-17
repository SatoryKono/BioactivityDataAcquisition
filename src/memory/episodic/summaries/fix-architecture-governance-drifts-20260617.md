---
id: fix-architecture-governance-drifts-20260617
title: Fix architecture governance drift after core split
task_id: fix-architecture-governance-drifts-20260617
created_at: '2026-06-17T12:28:15Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/application/core/batch_executor.py
- src/bioetl/interfaces/cli/commands/domains/diagnostics/operations.py
- scripts/data_quality/inventory_silver_filters_migration.py
- reports/quality/module-coverage-inventory.json
summary: Fixed DI inline runtime-state creation, private diagnostics import, regenerated
  coverage/scripts/silver/test-governance artifacts, ratcheted health server oversized
  LOC down, and validated targeted architecture guardrails.
---

# Episodic summary

## Task

- Title: Fix architecture governance drift after core split

## Outcome

- Fixed DI inline runtime-state creation, private diagnostics import, regenerated coverage/scripts/silver/test-governance artifacts, ratcheted health server oversized LOC down, and validated targeted architecture guardrails.

## Lessons learned

- Replace with durable follow-up if needed
