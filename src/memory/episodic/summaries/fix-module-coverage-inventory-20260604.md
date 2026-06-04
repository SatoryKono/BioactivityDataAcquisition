---
id: fix-module-coverage-inventory-20260604
title: Refresh module coverage inventory after source tree changes
task_id: fix-module-coverage-inventory-20260604
created_at: '2026-06-04T08:00:13Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Refreshed reports/quality/module-coverage-inventory.json from a targeted
  pytest-cov run with COVERAGE_FILE in /tmp to avoid mounted-checkout coverage DB
  corruption. Closed the reported test_module_coverage_inventory hash/hotspot failures
  locally; all hotspot family coverage gates now pass, including application_core
  182/182 measured and unexpected_unmeasured=0. Regenerated contract coverage matrix
  and architecture quality scorecard to clear related generated-artifact drift. Full
  sharded coverage-verify remains blocked by scripts catalog active_script_count 366
  > 364 and config-discrepancy baseline regression entity_effective inconsistent_parameter_count
  0 -> 148, so baseline was not increased.
---

# Episodic summary

## Task

- Title: Refresh module coverage inventory after source tree changes

## Outcome

- Refreshed reports/quality/module-coverage-inventory.json from a targeted pytest-cov run with COVERAGE_FILE in /tmp to avoid mounted-checkout coverage DB corruption. Closed the reported test_module_coverage_inventory hash/hotspot failures locally; all hotspot family coverage gates now pass, including application_core 182/182 measured and unexpected_unmeasured=0. Regenerated contract coverage matrix and architecture quality scorecard to clear related generated-artifact drift. Full sharded coverage-verify remains blocked by scripts catalog active_script_count 366 > 364 and config-discrepancy baseline regression entity_effective inconsistent_parameter_count 0 -> 148, so baseline was not increased.

## Lessons learned

- Replace with durable follow-up if needed
