# Dead Code Inventory

- snapshot_date: 2026-08-01
- linked_issue: #4541
- last_reviewed: 2026-08-01
- next_review_by: 2026-10-30
- review_cycle_days: 90
- triaged_entry_count: 18
- repo_wide_zero_import_candidate_count: 6
- repo_wide_classified_zero_import_candidate_count: 6
- repo_wide_untriaged_zero_import_candidate_count: 0
- repo_wide_owner_test_anchored_candidate_count: 6
- repo_wide_candidates_without_owner_tests_count: 0
- repo_wide_non_static_reachability_candidate_count: 5
- triaged_retained_owner_test_anchored_count: 14
- triaged_retained_without_owner_tests_count: 0
- note: zero static importer count is a review signal, not automatic removal proof
- guardrail: Zero static importer count is a review signal only; removals must still verify public entrypoints and dynamic/plugin import paths.

## Triage Verification

| Entry | Disposition | src importers | Verification |
| --- | --- | ---: | --- |
| `cached_bronze_support_active` | `retain_active` | 1 | `satisfied` |
| `error_handling_support_active` | `retain_active` | 2 | `satisfied` |
| `health_check_observability_active` | `retain_active` | 1 | `satisfied` |
| `health_check_policy_active` | `retain_active` | 1 | `satisfied` |
| `preflight_rules_removed` | `removed` | 0 | `not_applicable` |
| `checkpoint_service_support_removed` | `removed` | 0 | `not_applicable` |
| `checkpoint_state_codec_removed` | `removed` | 0 | `not_applicable` |
| `fsm_helper_active` | `retain_active` | 10 | `satisfied` |
| `runner_merge_stage_flow_removed` | `removed` | 0 | `not_applicable` |
| `column_priority_orderer_active` | `retain_active` | 2 | `satisfied` |
| `merger_input_mixin_active` | `retain_active` | 2 | `satisfied` |
| `runner_support_flow_active` | `retain_active` | 1 | `satisfied` |
| `runner_support_mixin_active` | `retain_active` | 1 | `satisfied` |
| `runner_support_policy_active` | `retain_active` | 1 | `satisfied` |
| `runner_support_runtime_active` | `retain_active` | 1 | `satisfied` |
| `runner_support_types_active` | `retain_active` | 5 | `satisfied` |
| `runtime_models_active` | `retain_active` | 39 | `satisfied` |
| `runtime_wiring_api_active` | `retain_active` | 18 | `satisfied` |

## Repo-wide Zero-import Candidates

| Module | Disposition | Path |
| --- | --- | --- |
| `bioetl.__main__` | `retain_module_entrypoint` | `src/bioetl/__main__.py` |
| `bioetl.application.services.control_plane.manifest.diagnostics.base` | `retain_dynamic_entrypoint` | `src/bioetl/application/services/control_plane/manifest/diagnostics/base.py` |
| `bioetl.application.services.control_plane.manifest.diagnostics.finalization` | `retain_dynamic_entrypoint` | `src/bioetl/application/services/control_plane/manifest/diagnostics/finalization.py` |
| `bioetl.application.services.control_plane.manifest.diagnostics.replay_refresh_support` | `retain_dynamic_entrypoint` | `src/bioetl/application/services/control_plane/manifest/diagnostics/replay_refresh_support.py` |
| `bioetl.interfaces.cli.commands.maintenance` | `retain_public_facade` | `src/bioetl/interfaces/cli/commands/maintenance.py` |
| `bioetl.domain.ports.stage_accounting` | `retain_canonical_owner_module` | `src/bioetl/domain/ports/stage_accounting.py` |

## Retained Owner-Test Evidence

| Scope | Module | Evidence Lane | Owner Tests |
| --- | --- | --- | --- |
| `triaged_retained` | `src/bioetl/infrastructure/adapters/_cached_bronze_support.py` | `retained_module_owner_suite` | `tests/architecture/test_wave4_complexity_closeout.py`, `tests/unit/infrastructure/adapters/test_cached_bronze_data_source.py` |
| `triaged_retained` | `src/bioetl/infrastructure/adapters/_error_handling_support.py` | `retained_module_owner_suite` | `tests/architecture/test_wave3_adapter_facade_closeout.py` |
| `triaged_retained` | `src/bioetl/infrastructure/adapters/_health_check_observability.py` | `retained_module_owner_suite` | `tests/architecture/test_wave3_adapter_facade_closeout.py` |
| `triaged_retained` | `src/bioetl/infrastructure/adapters/_health_check_policy.py` | `retained_module_owner_suite` | `tests/architecture/test_wave3_adapter_facade_closeout.py` |
| `triaged_retained` | `src/bioetl/application/composite/fsm_helper.py` | `retained_module_owner_suite` | `tests/unit/application/composite/test_fsm_helper.py`, `tests/unit/application/composite/test_runner_fsm.py` |
| `triaged_retained` | `src/bioetl/application/composite/column_priority_orderer.py` | `retained_module_owner_suite` | `tests/unit/application/composite/test_column_priority_orderer.py` |
| `triaged_retained` | `src/bioetl/application/composite/merger_input_mixin.py` | `retained_module_owner_suite` | `tests/unit/application/composite/test_merger_input_mixin.py` |
| `triaged_retained` | `src/bioetl/application/composite/runner_pkg/runner_support_flow.py` | `retained_module_owner_suite` | `tests/architecture/test_tracing_enforcement.py`, `tests/unit/application/composite/test_runner.py` |
| `triaged_retained` | `src/bioetl/application/composite/runner_pkg/runner_support_mixin.py` | `retained_module_owner_suite` | `tests/unit/application/composite/runner_pkg/test_runner_support_mixin.py` |
| `triaged_retained` | `src/bioetl/application/composite/runner_pkg/runner_support_policy.py` | `retained_module_owner_suite` | `tests/unit/application/composite/runner_pkg/test_runner_support_mixin.py`, `tests/unit/application/composite/test_runner.py` |
| `triaged_retained` | `src/bioetl/application/composite/runner_pkg/runner_support_runtime.py` | `retained_module_owner_suite` | `tests/architecture/test_replay_time_seam_inventory.py`, `tests/unit/application/composite/test_runner_checkpoint_resume.py` |
| `triaged_retained` | `src/bioetl/application/composite/runner_pkg/runner_support_types.py` | `retained_module_owner_suite` | `tests/unit/application/composite/runner_pkg/test_runner_support_mixin.py`, `tests/unit/application/composite/test_runner.py` |
| `triaged_retained` | `src/bioetl/application/composite/runtime_models.py` | `retained_module_owner_suite` | `tests/unit/application/composite/test_runtime_models.py` |
| `triaged_retained` | `src/bioetl/application/composite/runtime_wiring_api.py` | `retained_module_owner_suite` | `tests/architecture/test_composite_canonical_surfaces.py`, `tests/architecture/test_column_ordering_family.py`, `tests/unit/composition/bootstrap/runtime/test_composite_support_service_builders.py` |
| `repo_wide_zero_import` | `src/bioetl/__main__.py` | `module_entrypoint_owner_suite` | `tests/unit/interfaces/cli/test_cli_main_module.py` |
| `repo_wide_zero_import` | `src/bioetl/application/services/control_plane/manifest/diagnostics/base.py` | `dynamic_runtime_entrypoint` | `tests/architecture/test_control_plane_diagnostics_dynamic_loaders.py` |
| `repo_wide_zero_import` | `src/bioetl/application/services/control_plane/manifest/diagnostics/finalization.py` | `dynamic_runtime_entrypoint` | `tests/architecture/test_control_plane_diagnostics_dynamic_loaders.py` |
| `repo_wide_zero_import` | `src/bioetl/application/services/control_plane/manifest/diagnostics/replay_refresh_support.py` | `dynamic_runtime_entrypoint` | `tests/architecture/test_control_plane_diagnostics_dynamic_loaders.py` |
| `repo_wide_zero_import` | `src/bioetl/interfaces/cli/commands/maintenance.py` | `compatibility_facade_contract` | `tests/unit/interfaces/cli/commands/test_runtime_wrapper_contracts.py`, `tests/architecture/test_control_plane_diagnostics_dynamic_loaders.py` |
| `repo_wide_zero_import` | `src/bioetl/domain/ports/stage_accounting.py` | `canonical_owner_contract` | `tests/architecture/test_domain_public_api.py`, `tests/architecture/test_domain_ports_no_filesystem_or_engine_types.py`, `tests/architecture/test_port_contracts.py`, `tests/unit/domain/run_reports/test_stage_accounting.py`, `tests/architecture/test_runtime_checkable_completeness.py` |

## Non-Static Reachability Evidence

| Module | Disposition | Evidence Lane | Owner Tests |
| --- | --- | --- | --- |
| `bioetl.__main__` | `retain_module_entrypoint` | `module_entrypoint_owner_suite` | `tests/unit/interfaces/cli/test_cli_main_module.py` |
| `bioetl.application.services.control_plane.manifest.diagnostics.base` | `retain_dynamic_entrypoint` | `dynamic_runtime_entrypoint` | `tests/architecture/test_control_plane_diagnostics_dynamic_loaders.py` |
| `bioetl.application.services.control_plane.manifest.diagnostics.finalization` | `retain_dynamic_entrypoint` | `dynamic_runtime_entrypoint` | `tests/architecture/test_control_plane_diagnostics_dynamic_loaders.py` |
| `bioetl.application.services.control_plane.manifest.diagnostics.replay_refresh_support` | `retain_dynamic_entrypoint` | `dynamic_runtime_entrypoint` | `tests/architecture/test_control_plane_diagnostics_dynamic_loaders.py` |
| `bioetl.interfaces.cli.commands.maintenance` | `retain_public_facade` | `compatibility_facade_contract` | `tests/unit/interfaces/cli/commands/test_runtime_wrapper_contracts.py`, `tests/architecture/test_control_plane_diagnostics_dynamic_loaders.py` |
