---
id: fix-architecture-regressions-20260617
title: Fix architecture regressions after coverage burn-down
task_id: fix-architecture-regressions-20260617
created_at: '2026-06-17T07:48:06Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_issue_5272_application_core_coverage_closeout.py
- tests/architecture/test_module_coverage_inventory.py
- src/bioetl/composition/bootstrap/runtime/pipeline.py
- tests/unit/composition/factories/pipeline/test_registry.py
- Makefile
summary: 'Closed the pasted architecture regression set by restoring Makefile governance/live-ops
  targets, adding lifecycle registry entries for two non-active QA scripts, refreshing
  test-governance artifacts, making bootstrap_pipeline_runner visibly call prepare_runtime_registry
  while preserving compatibility-patch ordering, and covering registry_core edge cases
  so composition_factories_pipeline has zero unmeasured modules without increasing
  below-85 debt. Module coverage inventory now reports uncovered=0, unmeasured=0,
  composition_factories_pipeline threshold_status=pass, and #5272 closeout remains
  repo_uncovered=0/repo_unmeasured=0 with #5244 remaining_below_85=112.'
---

# Episodic summary

## Task

- Title: Fix architecture regressions after coverage burn-down

## Outcome

- Closed the pasted architecture regression set by restoring Makefile governance/live-ops targets, adding lifecycle registry entries for two non-active QA scripts, refreshing test-governance artifacts, making bootstrap_pipeline_runner visibly call prepare_runtime_registry while preserving compatibility-patch ordering, and covering registry_core edge cases so composition_factories_pipeline has zero unmeasured modules without increasing below-85 debt. Module coverage inventory now reports uncovered=0, unmeasured=0, composition_factories_pipeline threshold_status=pass, and #5272 closeout remains repo_uncovered=0/repo_unmeasured=0 with #5244 remaining_below_85=112.

## Lessons learned

- Replace with durable follow-up if needed
