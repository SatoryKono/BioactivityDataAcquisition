---
id: fix-reproducibility-golden-fixture-drift-20260617
title: Fix reproducibility golden fixture drift
task_id: fix-reproducibility-golden-fixture-drift-20260617
created_at: '2026-06-17T14:49:44Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/application/services/test_reproducibility_golden_fixtures.py
- tests/fixtures/golden/reproducibility/run_manifest_inspection_v1.json
summary: Synchronized run_manifest_inspection_v1 golden fixture with canonical structural_only_compat
  silver filter compatibility mode; target and related guard tests pass.
---

# Episodic summary

## Task

- Title: Fix reproducibility golden fixture drift

## Outcome

- Synchronized run_manifest_inspection_v1 golden fixture with canonical structural_only_compat silver filter compatibility mode; target and related guard tests pass.

## Lessons learned

- Replace with durable follow-up if needed
