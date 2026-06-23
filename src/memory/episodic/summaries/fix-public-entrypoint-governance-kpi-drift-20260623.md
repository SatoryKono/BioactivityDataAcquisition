---
id: fix-public-entrypoint-governance-kpi-drift-20260623
title: Fix public entrypoint governance KPI drift
task_id: fix-public-entrypoint-governance-kpi-drift-20260623
created_at: '2026-06-23T06:06:38Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/quality/debt_scorecard.yaml
summary: 'Synchronized configs/quality/debt_scorecard.yaml sanctioned_public_entrypoint_governance.metrics.narrow_first_party_callers_count
  with configs/quality/compatibility_facade_inventory.yaml. The burn-down plan has
  one row in target_state=narrow_first_party_callers, so current_count is now 1 and
  the rationale reflects the remaining maintenance_api governance row. Validation:
  target public-entrypoint KPI test passed, compatibility debt KPI test passed, scorecard
  baseline registry sync test passed, YAML parse passed.'
---

# Episodic summary

## Task

- Title: Fix public entrypoint governance KPI drift

## Outcome

- Synchronized configs/quality/debt_scorecard.yaml sanctioned_public_entrypoint_governance.metrics.narrow_first_party_callers_count with configs/quality/compatibility_facade_inventory.yaml. The burn-down plan has one row in target_state=narrow_first_party_callers, so current_count is now 1 and the rationale reflects the remaining maintenance_api governance row. Validation: target public-entrypoint KPI test passed, compatibility debt KPI test passed, scorecard baseline registry sync test passed, YAML parse passed.

## Lessons learned

- Replace with durable follow-up if needed
