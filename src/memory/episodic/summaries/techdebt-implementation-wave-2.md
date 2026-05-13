---
id: techdebt-implementation-wave-2
title: Remove legacy observe compatibility residues
task_id: techdebt-implementation-wave-2
created_at: '2026-05-13T14:51:00Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/application/services/control_plane/_run_manifest_diagnostics_replay_helpers.py
summary: 'Removed legacy_observe from active run-manifest diagnostics and reproducibility
  scoring surfaces, normalized removed checkpoint policy handling in test support,
  aligned run-manifest diagnostics/inspection expectations with normalization_profile
  fields, updated active CLI/contracts/runbook docs, and added an architecture guard
  preventing removed checkpoint policy modes from reappearing in active surfaces.
  Validation: bash scripts/engineering/dev/run_pytest.sh --skip-preflight tests/unit/application/services/test_run_manifest_inspection_service.py::test_show_resolves_manifest_by_run_id_and_includes_ledger_history
  tests/unit/application/services/test_run_manifest_inspection_service.py::test_show_by_manifest_id_without_ledger_port_returns_base_summary;
  bash scripts/engineering/dev/run_pytest.sh --skip-preflight tests/architecture/test_checkpoint_compatibility_policy_surface.py
  tests/unit/application/services/test_run_manifest_diagnostics.py tests/unit/infrastructure/test_config_settings.py
  tests/unit/composition/factories/pipeline/test_runner_assembly_unit.py. Refresh
  skipped because local memory refresh still fails on stale deleted path tests/e2e/test_checkpoint_e2e.py.'
---

# Episodic summary

## Task

- Title: Remove legacy observe compatibility residues

## Outcome

- Removed legacy_observe from active run-manifest diagnostics and reproducibility scoring surfaces, normalized removed checkpoint policy handling in test support, aligned run-manifest diagnostics/inspection expectations with normalization_profile fields, updated active CLI/contracts/runbook docs, and added an architecture guard preventing removed checkpoint policy modes from reappearing in active surfaces. Validation: bash scripts/engineering/dev/run_pytest.sh --skip-preflight tests/unit/application/services/test_run_manifest_inspection_service.py::test_show_resolves_manifest_by_run_id_and_includes_ledger_history tests/unit/application/services/test_run_manifest_inspection_service.py::test_show_by_manifest_id_without_ledger_port_returns_base_summary; bash scripts/engineering/dev/run_pytest.sh --skip-preflight tests/architecture/test_checkpoint_compatibility_policy_surface.py tests/unit/application/services/test_run_manifest_diagnostics.py tests/unit/infrastructure/test_config_settings.py tests/unit/composition/factories/pipeline/test_runner_assembly_unit.py. Refresh skipped because local memory refresh still fails on stale deleted path tests/e2e/test_checkpoint_e2e.py.

## Lessons learned

- Replace with durable follow-up if needed
