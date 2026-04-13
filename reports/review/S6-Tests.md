# Consolidated Review — S6: Tests

**Date**: 2026-04-13
**Sub-reviews**: 6 agents
**Status**: WARN
**Consolidated Score**: 6.4

## Sub-review Summary
| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
| S6.1 — Architecture | 210 | 8.5 | PASS | 0 | 105 |
| S6.2 — Unit Domain | 208 | 9.1 | PASS | 0 | 623 |
| S6.3 — Unit Application | 267 | 4.5 | FAIL | 5 | 1336 |
| S6.4 — Unit Infrastructure | 275 | 5.5 | FAIL | 3 | 827 |
| S6.5 — Unit Comp+Ifaces | 198 | 5.3 | FAIL | 4 | 731 |
| S6.6 — Integration+Other | 154 | 6.5 | WARN | 3 | 480 |

## Aggregated Issues
### Critical (MUST fix)
1. **AP-001** in `tests/unit/application/composite/test_runner_fsm.py:63` - Hard-coded dependency instantiation: CompositeCheckpointState()
2. **AP-001** in `tests/unit/application/composite/test_runner_robustness.py:63` - Hard-coded dependency instantiation: CompositeCheckpointState()
3. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_support_mixin.py:83` - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
4. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:33` - Hard-coded dependency instantiation: SeedResult()
5. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:50` - Hard-coded dependency instantiation: MergeResult()
6. **AP-001** in `tests/unit/infrastructure/adapters/openalex/test_client_helpers_adapter_mixin.py:21` - Hard-coded dependency instantiation: APIRequestCollector()
7. **AP-001** in `tests/unit/infrastructure/adapters/openalex/test_request_metadata.py:20` - Hard-coded dependency instantiation: APIRequestCollector()
8. **AP-001** in `tests/unit/infrastructure/storage/test_silver_writer_merged_mixin.py:21` - Hard-coded dependency instantiation: ArrowDataConverter()
9. **AP-001** in `tests/unit/interfaces/cli/commands/test_run_manifest_commands.py:36` - Hard-coded dependency instantiation: RunManifest()
10. **AP-001** in `tests/unit/interfaces/cli/commands/test_run_manifest_commands.py:55` - Hard-coded dependency instantiation: RunLedgerEntry()
11. **AP-001** in `tests/unit/interfaces/cli/commands/test_lineage_commands.py:34` - Hard-coded dependency instantiation: LineageNodeRef()
12. **AP-001** in `tests/unit/interfaces/cli/commands/test_lineage_commands.py:38` - Hard-coded dependency instantiation: LineageGraphFragment()
13. **AP-001** in `tests/integration/interfaces/test_cli_run_manifest.py:28` - Hard-coded dependency instantiation: RunID()
14. **AP-001** in `tests/integration/interfaces/test_cli_run_manifest.py:29` - Hard-coded dependency instantiation: RunManifest()
15. **AP-001** in `tests/integration/ci/test_reproducibility_contract_suite.py:102` - Hard-coded dependency instantiation: RunID()
