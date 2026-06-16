# Dead Code Inventory

- snapshot_date: 2026-06-16
- linked_issue: #4541
- last_reviewed: 2026-06-16
- next_review_by: 2026-09-14
- review_cycle_days: 90
- triaged_entry_count: 18
- repo_wide_zero_import_candidate_count: 2
- repo_wide_classified_zero_import_candidate_count: 2
- repo_wide_untriaged_zero_import_candidate_count: 0
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
