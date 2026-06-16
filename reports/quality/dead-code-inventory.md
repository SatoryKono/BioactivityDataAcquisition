# Dead Code Inventory

- snapshot_date: 2026-06-16
- linked_issue: #4541
- last_reviewed: 2026-06-16
- next_review_by: 2026-09-14
- review_cycle_days: 90
- triaged_entry_count: 18
- repo_wide_zero_import_candidate_count: 13
- repo_wide_classified_zero_import_candidate_count: 13
- repo_wide_untriaged_zero_import_candidate_count: 0
- repo_wide_owner_test_anchored_candidate_count: 13
- repo_wide_candidates_without_owner_tests_count: 0
- repo_wide_non_static_reachability_candidate_count: 2
- triaged_retained_owner_test_anchored_count: 14
- triaged_retained_without_owner_tests_count: 0
- note: zero static importer count is a review signal, not automatic removal proof
- guardrail: Zero static importer count is a review signal only; removals must still verify public entrypoints and dynamic/plugin import paths.

## Triage Verification

| Entry | Disposition | src importers | Verification |
| --- | --- | ---: | --- |
| `cached_bronze_support_active` | `retain_active` | 1 | `satisfied` |
| `error_handling_support_active` | `retain_active` | 1 | `satisfied` |
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
| `runner_support_types_active` | `retain_active` | 4 | `satisfied` |
| `runtime_models_active` | `retain_active` | 39 | `satisfied` |
| `runtime_wiring_api_active` | `retain_active` | 18 | `satisfied` |

## Repo-wide Zero-import Candidates

| Module | Disposition | Path |
| --- | --- | --- |
| `bioetl.__main__` | `retain_module_entrypoint` | `src/bioetl/__main__.py` |
| `bioetl.composition.registry` | `retain_public_facade` | `src/bioetl/composition/registry.py` |
| `bioetl.domain.ports.data_normalization` | `retain_canonical_owner_module` | `src/bioetl/domain/ports/data_normalization.py` |
| `bioetl.domain.ports.data_source` | `retain_canonical_owner_module` | `src/bioetl/domain/ports/data_source.py` |
| `bioetl.domain.ports.delta_reader` | `retain_canonical_owner_module` | `src/bioetl/domain/ports/delta_reader.py` |
| `bioetl.domain.ports.export` | `retain_canonical_owner_module` | `src/bioetl/domain/ports/export.py` |
| `bioetl.domain.ports.filtering` | `retain_canonical_owner_module` | `src/bioetl/domain/ports/filtering.py` |
| `bioetl.domain.ports.idmapping` | `retain_canonical_owner_module` | `src/bioetl/domain/ports/idmapping.py` |
| `bioetl.domain.ports.logger_port` | `retain_canonical_owner_module` | `src/bioetl/domain/ports/logger_port.py` |
| `bioetl.domain.ports.pii` | `retain_canonical_owner_module` | `src/bioetl/domain/ports/pii.py` |
| `bioetl.domain.ports.protein_classification` | `retain_canonical_owner_module` | `src/bioetl/domain/ports/protein_classification.py` |
| `bioetl.domain.ports.publication_strategy` | `retain_canonical_owner_module` | `src/bioetl/domain/ports/publication_strategy.py` |
| `bioetl.domain.ports.resilience` | `retain_canonical_owner_module` | `src/bioetl/domain/ports/resilience.py` |

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
| `repo_wide_zero_import` | `src/bioetl/__main__.py` | `module_entrypoint_owner_suite` | `tests/unit/interfaces/cli/test_cli_commands_basic.py`, `tests/unit/interfaces/cli/test_cli_helpers.py` |
| `repo_wide_zero_import` | `src/bioetl/composition/registry.py` | `compatibility_facade_contract` | `tests/architecture/test_compatibility_freeze_guards.py`, `tests/unit/composition/test_canonical_module_paths.py` |
| `repo_wide_zero_import` | `src/bioetl/domain/ports/data_normalization.py` | `canonical_owner_contract` | `tests/architecture/test_domain_public_api.py`, `tests/architecture/test_domain_ports_no_filesystem_or_engine_types.py`, `tests/architecture/test_port_contracts.py` |
| `repo_wide_zero_import` | `src/bioetl/domain/ports/data_source.py` | `canonical_owner_contract` | `tests/architecture/test_domain_public_api.py`, `tests/architecture/test_domain_ports_no_filesystem_or_engine_types.py`, `tests/architecture/test_port_contracts.py` |
| `repo_wide_zero_import` | `src/bioetl/domain/ports/delta_reader.py` | `canonical_owner_contract` | `tests/architecture/test_domain_public_api.py`, `tests/architecture/test_domain_ports_no_filesystem_or_engine_types.py`, `tests/architecture/test_port_contracts.py` |
| `repo_wide_zero_import` | `src/bioetl/domain/ports/export.py` | `canonical_owner_contract` | `tests/architecture/test_domain_public_api.py`, `tests/architecture/test_domain_ports_no_filesystem_or_engine_types.py`, `tests/architecture/test_port_contracts.py` |
| `repo_wide_zero_import` | `src/bioetl/domain/ports/filtering.py` | `canonical_owner_contract` | `tests/architecture/test_domain_public_api.py`, `tests/architecture/test_domain_ports_no_filesystem_or_engine_types.py`, `tests/architecture/test_port_contracts.py` |
| `repo_wide_zero_import` | `src/bioetl/domain/ports/idmapping.py` | `canonical_owner_contract` | `tests/architecture/test_domain_public_api.py`, `tests/architecture/test_domain_ports_no_filesystem_or_engine_types.py`, `tests/architecture/test_port_contracts.py` |
| `repo_wide_zero_import` | `src/bioetl/domain/ports/logger_port.py` | `canonical_owner_contract` | `tests/architecture/test_domain_public_api.py`, `tests/architecture/test_domain_ports_no_filesystem_or_engine_types.py`, `tests/architecture/test_port_contracts.py` |
| `repo_wide_zero_import` | `src/bioetl/domain/ports/pii.py` | `canonical_owner_contract` | `tests/architecture/test_domain_public_api.py`, `tests/architecture/test_domain_ports_no_filesystem_or_engine_types.py`, `tests/architecture/test_port_contracts.py` |
| `repo_wide_zero_import` | `src/bioetl/domain/ports/protein_classification.py` | `canonical_owner_contract` | `tests/architecture/test_domain_public_api.py`, `tests/architecture/test_domain_ports_no_filesystem_or_engine_types.py`, `tests/architecture/test_port_contracts.py` |
| `repo_wide_zero_import` | `src/bioetl/domain/ports/publication_strategy.py` | `canonical_owner_contract` | `tests/architecture/test_domain_public_api.py`, `tests/architecture/test_domain_ports_no_filesystem_or_engine_types.py`, `tests/architecture/test_port_contracts.py` |
| `repo_wide_zero_import` | `src/bioetl/domain/ports/resilience.py` | `canonical_owner_contract` | `tests/architecture/test_domain_public_api.py`, `tests/architecture/test_domain_ports_no_filesystem_or_engine_types.py`, `tests/architecture/test_port_contracts.py` |

## Non-Static Reachability Evidence

| Module | Disposition | Evidence Lane | Owner Tests |
| --- | --- | --- | --- |
| `bioetl.__main__` | `retain_module_entrypoint` | `module_entrypoint_owner_suite` | `tests/unit/interfaces/cli/test_cli_commands_basic.py`, `tests/unit/interfaces/cli/test_cli_helpers.py` |
| `bioetl.composition.registry` | `retain_public_facade` | `compatibility_facade_contract` | `tests/architecture/test_compatibility_freeze_guards.py`, `tests/unit/composition/test_canonical_module_paths.py` |
