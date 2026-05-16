# Consolidated Review — S6: Tests

**Date**: 2026-05-16
**Sub-reviews**: 6 agents
**Status**: WARN
**Consolidated Score**: 6.3

## Sub-review Summary
| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
| S6.1 — Architecture | 296 | 8.4 | PASS | 0 | 193 |
| S6.2 — Unit Domain | 251 | 8.9 | PASS | 0 | 645 |
| S6.3 — Unit Application | 308 | 4.5 | FAIL | 5 | 1332 |
| S6.4 — Unit Infrastructure | 289 | 5.2 | FAIL | 3 | 863 |
| S6.5 — Unit Comp+Ifaces | 193 | 5.0 | FAIL | 4 | 760 |
| S6.6 — Integration+Other | 254 | 5.5 | FAIL | 3 | 672 |

## Aggregated Issues
### Critical (MUST fix)
1. **AP-001** in `tests/unit/application/composite/runner_test_support.py:52` - Hard-coded dependency instantiation: CompositeCheckpointState()
2. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_merge_stage_mixin.py:79` - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
3. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_stage_start_flow.py:24` - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
4. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:34` - Hard-coded dependency instantiation: SeedResult()
5. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:51` - Hard-coded dependency instantiation: MergeResult()
6. **AP-001** in `tests/unit/infrastructure/adapters/openalex/test_client_helpers_adapter_mixin.py:28` - Hard-coded dependency instantiation: APIRequestCollector()
7. **AP-001** in `tests/unit/infrastructure/adapters/openalex/test_request_metadata.py:21` - Hard-coded dependency instantiation: APIRequestCollector()
8. **AP-001** in `tests/unit/infrastructure/storage/test_silver_writer_merged_mixin.py:25` - Hard-coded dependency instantiation: ArrowDataConverter()
9. **AP-001** in `tests/unit/interfaces/cli/commands/test_run_manifest_commands.py:45` - Hard-coded dependency instantiation: RunManifest()
10. **AP-001** in `tests/unit/interfaces/cli/commands/test_run_manifest_commands.py:66` - Hard-coded dependency instantiation: RunLedgerEntry()
11. **AP-001** in `tests/unit/interfaces/cli/commands/test_lineage_commands.py:34` - Hard-coded dependency instantiation: LineageNodeRef()
12. **AP-001** in `tests/unit/interfaces/cli/commands/test_lineage_commands.py:38` - Hard-coded dependency instantiation: LineageGraphFragment()
13. **AP-001** in `tests/integration/interfaces/test_cli_run_manifest.py:29` - Hard-coded dependency instantiation: RunID()
14. **AP-001** in `tests/integration/interfaces/test_cli_run_manifest.py:30` - Hard-coded dependency instantiation: RunManifest()
15. **AP-001** in `tests/integration/ci/reproducibility_contract_support.py:72` - Hard-coded dependency instantiation: RunID()
