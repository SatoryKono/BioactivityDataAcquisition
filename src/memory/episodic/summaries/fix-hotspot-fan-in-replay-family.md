---
id: fix-hotspot-fan-in-replay-family
title: Fix hotspot fan-in replay_family regression
task_id: fix-hotspot-fan-in-replay-family
created_at: '2026-06-16T19:04:14Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_hotspot_fan_in_family_ratchets.py
- scripts/engineering/qa/report_module_coverage_inventory.py
- reports/quality/module-coverage-inventory.json
summary: 'Resolved the application_services_control_plane fan-in ratchet without raising
  debt budgets. Live diagnostics fan-in is max=4: persistence_policy=3, replay_family=4,
  replay_blockers=4, and tests/architecture/test_hotspot_fan_in_family_ratchets.py
  passes. Kept source module count at 2147 with unmeasured_module_count=0, stabilized
  module coverage status_counts to include zero-valued statuses, refreshed module-coverage
  inventory and architecture-quality-scorecard artifacts, and updated issue #5265
  closeout metrics to the live inventory. Validation passed: targeted ruff, report-module-coverage
  --check, hotspot fan-in guard, module coverage inventory guards with expected WSL
  hash skip, architecture quality scorecard guard, #5265 closeout guard, related control-plane/domain
  unit tests, and report-module-coverage generator unit tests. No debt budgets were
  increased.'
---

# Episodic summary

## Task

- Title: Fix hotspot fan-in replay_family regression

## Outcome

- Resolved the application_services_control_plane fan-in ratchet without raising debt budgets. Live diagnostics fan-in is max=4: persistence_policy=3, replay_family=4, replay_blockers=4, and tests/architecture/test_hotspot_fan_in_family_ratchets.py passes. Kept source module count at 2147 with unmeasured_module_count=0, stabilized module coverage status_counts to include zero-valued statuses, refreshed module-coverage inventory and architecture-quality-scorecard artifacts, and updated issue #5265 closeout metrics to the live inventory. Validation passed: targeted ruff, report-module-coverage --check, hotspot fan-in guard, module coverage inventory guards with expected WSL hash skip, architecture quality scorecard guard, #5265 closeout guard, related control-plane/domain unit tests, and report-module-coverage generator unit tests. No debt budgets were increased.

## Lessons learned

- Replace with durable follow-up if needed
