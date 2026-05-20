---
id: arch-budgets-fix-20260520
title: Fix architecture regression batch
task_id: arch-budgets-fix-20260520
created_at: '2026-05-20T07:43:16Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/application/core/batch_writer_columns_mixin.py
- src/bioetl/application/services/lineage/metadata_context.py
- src/bioetl/application/services/lineage/metadata_coordinator.py
- src/bioetl/domain/control_plane/run_ledger_replay.py
- tests/architecture/test_layer_dependencies.py
- scripts/engineering/qa/check_naming_package_consistency.py
- configs/quality/integration_vcr_policy.yaml
summary: Closed Any budget, LOC, naming/DI, inventory, and consistency-gate regressions
  in the current architecture test batch.
---

# Episodic summary

## Task

- Title: Fix architecture regression batch

## Outcome

- Closed Any budget, LOC, naming/DI, inventory, and consistency-gate regressions in the current architecture test batch.

## Lessons learned

- Replace with durable follow-up if needed
