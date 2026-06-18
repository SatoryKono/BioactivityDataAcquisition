---
id: fix-track-d-fixture-control-plane-nameerror
title: Fix tracked fixture control plane linkage NameError
task_id: fix-track-d-fixture-control-plane-nameerror
created_at: '2026-06-18T17:54:21Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/integration/ci/test_track_d_fixture_control_plane_linkage.py
summary: 'Investigated reported Windows pytest NameError for assess_reproducibility_policy
  in Track D fixture control-plane linkage tests. Current checkout imports the policy
  helper correctly from _run_manifest_replay_support and _run_manifest_builder_policy;
  targeted WSL and Windows pytest runs pass, so reported failure is stale checkout/cache/environment
  rather than a current source regression. Validation: Windows .venv-win/Scripts/python.exe
  -m pytest tests/integration/ci/test_track_d_fixture_control_plane_linkage.py -q
  --tb=short --disable-warnings => 5 passed; WSL run_pytest narrow file => 5 passed.'
---

# Episodic summary

## Task

- Title: Fix tracked fixture control plane linkage NameError

## Outcome

- Investigated reported Windows pytest NameError for assess_reproducibility_policy in Track D fixture control-plane linkage tests. Current checkout imports the policy helper correctly from _run_manifest_replay_support and _run_manifest_builder_policy; targeted WSL and Windows pytest runs pass, so reported failure is stale checkout/cache/environment rather than a current source regression. Validation: Windows .venv-win/Scripts/python.exe -m pytest tests/integration/ci/test_track_d_fixture_control_plane_linkage.py -q --tb=short --disable-warnings => 5 passed; WSL run_pytest narrow file => 5 passed.

## Lessons learned

- Replace with durable follow-up if needed
