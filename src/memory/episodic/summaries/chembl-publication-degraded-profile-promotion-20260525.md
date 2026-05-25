---
id: chembl-publication-degraded-profile-promotion-20260525
title: Debug chembl_publication degraded_observable profile promotion failure
task_id: chembl-publication-degraded-profile-promotion-20260525
created_at: '2026-05-25T05:11:43Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/domain/control_plane/_reproducibility_policy_profiles.py
- src/bioetl/application/services/control_plane/run_manifest_service.py
- src/bioetl/composition/runtime_builders/_run_manifest_builder_policy.py
- src/bioetl/composition/runtime_builders/runner_builder.py
- src/bioetl/interfaces/cli/commands/_workflow_run_support.py
- tests/unit/composition/runtime_builders/test_runner_builder_persistence_profile.py
summary: Implemented explicit local diagnostic degraded_observable opt-down handling
  for non-exact non-critical pipeline/workflow launches. Per-run degraded overrides
  now remain degraded through workflow preflight, runner input preparation, manifest
  launch context, and RunManifestService replay-capable floor validation via required_persistence_profile_opt_down.
  Exact replay and critical runtimes still promote to replay_ready. Added unit coverage
  for domain resolver, RunManifestService, runner builder dirty-source diagnostic
  opt-down, workflow CLI acceptance, and strict promotion regressions. Synced CLI/run-manifest
  docs.
---

# Episodic summary

## Task

- Title: Debug chembl_publication degraded_observable profile promotion failure

## Outcome

- Implemented explicit local diagnostic degraded_observable opt-down handling for non-exact non-critical pipeline/workflow launches. Per-run degraded overrides now remain degraded through workflow preflight, runner input preparation, manifest launch context, and RunManifestService replay-capable floor validation via required_persistence_profile_opt_down. Exact replay and critical runtimes still promote to replay_ready. Added unit coverage for domain resolver, RunManifestService, runner builder dirty-source diagnostic opt-down, workflow CLI acceptance, and strict promotion regressions. Synced CLI/run-manifest docs.

## Lessons learned

- Replace with durable follow-up if needed
