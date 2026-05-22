---
id: debug-e2e-replay-ready-manifest-20260522
title: Debug chembl_activity e2e replay_ready manifest failure
task_id: debug-e2e-replay-ready-manifest-20260522
created_at: '2026-05-22T10:39:07Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/e2e/test_advanced_scenarios_e2e.py
- tests/e2e/conftest.py
- tests/e2e/test_e2e_stability_policy.py
summary: Added E2E classification for strict persistence snapshot gaps, routed advanced
  scenario runs through a skip-on-policy-envelope helper, and verified advanced_scenarios
  now passes or skips deterministically under replay_ready snapshot requirements.
---

# Episodic summary

## Task

- Title: Debug chembl_activity e2e replay_ready manifest failure

## Outcome

- Added E2E classification for strict persistence snapshot gaps, routed advanced scenario runs through a skip-on-policy-envelope helper, and verified advanced_scenarios now passes or skips deterministically under replay_ready snapshot requirements.

## Lessons learned

- Replace with durable follow-up if needed
