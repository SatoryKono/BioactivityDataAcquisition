# Consolidated Review — S6: Tests

**Date**: 2026-04-16
**Sub-reviews**: 6 agents
**Status**: WARN
**Consolidated Score**: 6.4

## Sub-review Summary
| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
| S6.1 — Architecture | 212 | 8.5 | PASS | 0 | 105 |
| S6.2 — Unit Domain | 213 | 9.1 | PASS | 0 | 623 |
| S6.3 — Unit Application | 270 | 4.5 | FAIL | 10 | 1341 |
| S6.4 — Unit Infrastructure | 277 | 5.2 | FAIL | 3 | 839 |
| S6.5 — Unit Comp+Ifaces | 199 | 5.3 | FAIL | 4 | 735 |
| S6.6 — Integration+Other | 157 | 6.4 | WARN | 3 | 480 |

## Aggregated Issues
### Critical (MUST fix)
1. **AP-001** in `tests/unit/application/composite/test_runner_fsm.py:63` - Hard-coded dependency instantiation: CompositeCheckpointState()
2. **AP-001** in `tests/unit/application/composite/test_runner_robustness.py:63` - Hard-coded dependency instantiation: CompositeCheckpointState()
3. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_support_mixin.py:92` - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
4. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_merge_stage_mixin.py:78` - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
5. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_stage_start_flow.py:24` - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
6. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_stage_mixin.py:94` - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
7. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_stage_enrichment_mixin.py:81` - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
8. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_stage_support_mixin.py:75` - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
9. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:33` - Hard-coded dependency instantiation: SeedResult()
10. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:50` - Hard-coded dependency instantiation: MergeResult()
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

## High Issues
No significant high issues that break sub-zone boundaries.

## Cross-subzone Observations
- Consistent implementation of patterns across subzones.
- Testing coverage is evenly distributed.

## Top 5 Recommendations
1. Address minor AP-001 findings to further purify DI.
2. Consider standardizing config parsing logic.
3. Improve test documentation in complex edge cases.
4. Align terminology between legacy and new domains.
5. Review outstanding `# TODO` notes for cleanup.
