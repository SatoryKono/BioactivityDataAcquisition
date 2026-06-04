---
id: fix-hotspot-family-baseline-drift
title: Fix hotspot family baseline drift
task_id: fix-hotspot-family-baseline-drift
created_at: '2026-06-04T18:55:01Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/quality/debt_scorecard.yaml
summary: Synchronized hotspot family scorecard actual metrics and generated baseline
  artifacts for current collector output. Updated application_core to 21902 LOC/0.344
  helper ratio and composition_bootstrap_runtime to 6005 LOC without changing bounded-growth
  budgets. Verified report-family-baseline --check and targeted quality debt scorecard
  pytest.
---

# Episodic summary

## Task

- Title: Fix hotspot family baseline drift

## Outcome

- Synchronized hotspot family scorecard actual metrics and generated baseline artifacts for current collector output. Updated application_core to 21902 LOC/0.344 helper ratio and composition_bootstrap_runtime to 6005 LOC without changing bounded-growth budgets. Verified report-family-baseline --check and targeted quality debt scorecard pytest.

## Lessons learned

- Replace with durable follow-up if needed
