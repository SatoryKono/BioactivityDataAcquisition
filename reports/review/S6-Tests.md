# Consolidated Review — S6: Tests

**Date**: 2026-04-28
**Sub-reviews**: 6 agents
**Status**: WARN
**Consolidated Score**: 6.3

## Sub-review Summary
| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
| S6.1 — Architecture | 237 | 8.5 | PASS | 0 | 124 |
| S6.2 — Unit Domain | 229 | 8.9 | PASS | 0 | 633 |
| S6.3 — Unit Application | 277 | 4.5 | FAIL | 9 | 1333 |
| S6.4 — Unit Infrastructure | 282 | 5.2 | FAIL | 3 | 844 |
| S6.5 — Unit Comp+Ifaces | 180 | 5.0 | FAIL | 4 | 752 |
| S6.6 — Integration+Other | 184 | 5.7 | FAIL | 3 | 632 |

## Aggregated Issues
### Critical (MUST fix)
1. **AP-001** in `tests/unit/application/composite/runner_test_support.py:47` - Hard-coded dependency instantiation: CompositeCheckpointState()
2. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_support_mixin.py:92` - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
3. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_merge_stage_mixin.py:79` - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
4. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_stage_start_flow.py:24` - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
5. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_stage_mixin.py:95` - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
6. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_stage_enrichment_mixin.py:82` - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
7. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_stage_support_mixin.py:92` - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
8. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:34` - Hard-coded dependency instantiation: SeedResult()
9. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:51` - Hard-coded dependency instantiation: MergeResult()
10. **AP-001** in `tests/unit/infrastructure/adapters/openalex/test_client_helpers_adapter_mixin.py:23` - Hard-coded dependency instantiation: APIRequestCollector()
11. **AP-001** in `tests/unit/infrastructure/adapters/openalex/test_request_metadata.py:20` - Hard-coded dependency instantiation: APIRequestCollector()
12. **AP-001** in `tests/unit/infrastructure/storage/test_silver_writer_merged_mixin.py:23` - Hard-coded dependency instantiation: ArrowDataConverter()
13. **AP-001** in `tests/unit/interfaces/cli/commands/test_run_manifest_commands.py:43` - Hard-coded dependency instantiation: RunManifest()
14. **AP-001** in `tests/unit/interfaces/cli/commands/test_run_manifest_commands.py:64` - Hard-coded dependency instantiation: RunLedgerEntry()
15. **AP-001** in `tests/unit/interfaces/cli/commands/test_lineage_commands.py:34` - Hard-coded dependency instantiation: LineageNodeRef()
16. **AP-001** in `tests/unit/interfaces/cli/commands/test_lineage_commands.py:38` - Hard-coded dependency instantiation: LineageGraphFragment()
17. **AP-001** in `tests/integration/interfaces/test_cli_run_manifest.py:28` - Hard-coded dependency instantiation: RunID()
18. **AP-001** in `tests/integration/interfaces/test_cli_run_manifest.py:29` - Hard-coded dependency instantiation: RunManifest()
19. **AP-001** in `tests/integration/ci/test_reproducibility_contract_suite.py:130` - Hard-coded dependency instantiation: RunID()
