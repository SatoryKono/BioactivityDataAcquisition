# Consolidated Review — S6: Tests

**Date**: 2026-04-18
**Sub-reviews**: 6 agents
**Status**: WARN
**Consolidated Score**: 6.4

## Sub-review Summary
| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
| S6.1 — Architecture | 212 | 8.5 | PASS | 0 | 105 |
| S6.2 — Unit Domain | 213 | 9.1 | PASS | 0 | 613 |
| S6.3 — Unit Application | 270 | 4.5 | FAIL | 10 | 1341 |
| S6.4 — Unit Infrastructure | 277 | 5.2 | FAIL | 3 | 846 |
| S6.5 — Unit Comp+Ifaces | 199 | 5.3 | FAIL | 4 | 737 |
| S6.6 — Integration+Other | 157 | 6.4 | WARN | 3 | 540 |

## Aggregated Issues
### Critical (MUST fix)
1. **AP-001** in `tests/unit/application/composite/test_runner_fsm.py:65` - Hard-coded dependency instantiation: CompositeCheckpointState()
2. **AP-001** in `tests/unit/application/composite/test_runner_robustness.py:64` - Hard-coded dependency instantiation: CompositeCheckpointState()
3. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_support_mixin.py:92` - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
4. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_merge_stage_mixin.py:79` - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
5. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_stage_start_flow.py:24` - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
6. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_stage_mixin.py:95` - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
7. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_stage_enrichment_mixin.py:82` - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
8. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_stage_support_mixin.py:92` - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
9. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:34` - Hard-coded dependency instantiation: SeedResult()
10. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:51` - Hard-coded dependency instantiation: MergeResult()
11. **AP-001** in `tests/unit/infrastructure/adapters/openalex/test_client_helpers_adapter_mixin.py:21` - Hard-coded dependency instantiation: APIRequestCollector()
12. **AP-001** in `tests/unit/infrastructure/adapters/openalex/test_request_metadata.py:20` - Hard-coded dependency instantiation: APIRequestCollector()
13. **AP-001** in `tests/unit/infrastructure/storage/test_silver_writer_merged_mixin.py:21` - Hard-coded dependency instantiation: ArrowDataConverter()
14. **AP-001** in `tests/unit/interfaces/cli/commands/test_run_manifest_commands.py:36` - Hard-coded dependency instantiation: RunManifest()
15. **AP-001** in `tests/unit/interfaces/cli/commands/test_run_manifest_commands.py:57` - Hard-coded dependency instantiation: RunLedgerEntry()
16. **AP-001** in `tests/unit/interfaces/cli/commands/test_lineage_commands.py:34` - Hard-coded dependency instantiation: LineageNodeRef()
17. **AP-001** in `tests/unit/interfaces/cli/commands/test_lineage_commands.py:38` - Hard-coded dependency instantiation: LineageGraphFragment()
18. **AP-001** in `tests/integration/interfaces/test_cli_run_manifest.py:28` - Hard-coded dependency instantiation: RunID()
19. **AP-001** in `tests/integration/interfaces/test_cli_run_manifest.py:29` - Hard-coded dependency instantiation: RunManifest()
20. **AP-001** in `tests/integration/ci/test_reproducibility_contract_suite.py:116` - Hard-coded dependency instantiation: RunID()

### High
1. **TYPE-002** in `tests/architecture/test_pipeline_source_override_policy.py:21` - Usage of Any without comment justification.
2. **TYPE-002** in `tests/architecture/test_explicit_gold_scd2_policy.py:58` - Usage of Any without comment justification.
3. **TYPE-002** in `tests/architecture/test_explicit_gold_scd2_policy.py:67` - Usage of Any without comment justification.
4. **TYPE-002** in `tests/architecture/test_composite_dq_externalization.py:18` - Usage of Any without comment justification.
5. **TYPE-002** in `tests/architecture/test_composite_dq_externalization.py:41` - Usage of Any without comment justification.
6. **TYPE-001** in `tests/architecture/test_interfaces_no_infrastructure.py:51` - Public function 'test_cli_no_infrastructure_imports' lacks return type annotation.
7. **TYPE-001** in `tests/architecture/test_interfaces_no_infrastructure.py:69` - Public function 'test_cli_no_bootstrap_internal_imports' lacks return type annotation.
8. **TYPE-001** in `tests/architecture/test_interfaces_no_infrastructure.py:88` - Public function 'test_all_cli_commands_no_infrastructure_imports' lacks return type annotation.
9. **TYPE-001** in `tests/architecture/test_interfaces_no_infrastructure.py:118` - Public function 'test_legacy_cli_infrastructure_imports_documented' lacks return type annotation.
10. **TYPE-001** in `tests/architecture/test_interfaces_no_infrastructure.py:166` - Public function 'test_interfaces_module_no_infrastructure_imports' lacks return type annotation.
11. **TYPE-001** in `tests/architecture/test_interfaces_no_infrastructure.py:182` - Public function 'test_observability_no_infrastructure_imports' lacks return type annotation.
12. **TYPE-001** in `tests/architecture/test_interfaces_no_infrastructure.py:203` - Public function 'test_checkpoint_service_exists' lacks return type annotation.
13. **TYPE-001** in `tests/architecture/test_interfaces_no_infrastructure.py:208` - Public function 'test_quarantine_service_exists' lacks return type annotation.
14. **TYPE-001** in `tests/architecture/test_interfaces_no_infrastructure.py:213` - Public function 'test_lock_service_exists' lacks return type annotation.
15. **TYPE-001** in `tests/architecture/test_interfaces_no_infrastructure.py:218` - Public function 'test_bronze_cleanup_service_exists' lacks return type annotation.
16. **TYPE-001** in `tests/architecture/test_interfaces_no_infrastructure.py:230` - Public function 'test_entrypoints_exports_services' lacks return type annotation.
17. **TYPE-001** in `tests/architecture/test_interfaces_no_infrastructure.py:245` - Public function 'test_entrypoints_all_excludes_legacy_service_getters' lacks return type annotation.
18. **TYPE-001** in `tests/architecture/test_interfaces_no_infrastructure.py:304` - Public function 'test_http_init_no_runtime_infrastructure_imports' lacks return type annotation.
19. **TYPE-001** in `tests/architecture/test_interfaces_no_infrastructure.py:321` - Public function 'test_http_types_no_runtime_infrastructure_imports' lacks return type annotation.
20. **TYPE-001** in `tests/architecture/test_interfaces_no_infrastructure.py:338` - Public function 'test_health_server_no_runtime_infrastructure_imports' lacks return type annotation.

## Cross-subzone Observations
No significant cross-subzone issues found.

## Top 5 Recommendations
1. Address critical issues immediately.
2. Review high issues.
