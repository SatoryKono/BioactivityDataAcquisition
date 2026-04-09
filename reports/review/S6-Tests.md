# Consolidated Review — S6: Tests

**Date**: 2026-04-09
**Sub-reviews**: 6 agents
**Status**: WARN
**Consolidated Score**: 6.7

## Sub-review Summary
| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
| S6.1 — Architecture | 202 | 8.5 | PASS | 0 | 99 |
| S6.2 — Unit Domain | 196 | 9.1 | PASS | 0 | 616 |
| S6.3 — Unit Application | 254 | 5.0 | FAIL | 4 | 1326 |
| S6.4 — Unit Infrastructure | 268 | 5.5 | FAIL | 3 | 834 |
| S6.5 — Unit Comp+Ifaces | 191 | 5.6 | FAIL | 4 | 710 |
| S6.6 — Integration+Other | 152 | 7.3 | WARN | 2 | 480 |

## Aggregated Issues
### Critical (MUST fix)
1. **AP-001** in `tests/unit/application/composite/test_runner_fsm.py:63` - Hard-coded dependency instantiation: CompositeCheckpointState()
2. **AP-001** in `tests/unit/application/composite/test_runner_robustness.py:63` - Hard-coded dependency instantiation: CompositeCheckpointState()
3. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:33` - Hard-coded dependency instantiation: SeedResult()
4. **AP-001** in `tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:50` - Hard-coded dependency instantiation: MergeResult()
5. **AP-001** in `tests/unit/infrastructure/adapters/openalex/test_client_helpers_adapter_mixin.py:21` - Hard-coded dependency instantiation: APIRequestCollector()
6. **AP-001** in `tests/unit/infrastructure/adapters/openalex/test_request_metadata.py:20` - Hard-coded dependency instantiation: APIRequestCollector()
7. **AP-001** in `tests/unit/infrastructure/storage/test_silver_writer_merged_mixin.py:21` - Hard-coded dependency instantiation: ArrowDataConverter()
8. **AP-001** in `tests/unit/interfaces/cli/commands/test_run_manifest_commands.py:31` - Hard-coded dependency instantiation: RunManifest()
9. **AP-001** in `tests/unit/interfaces/cli/commands/test_run_manifest_commands.py:50` - Hard-coded dependency instantiation: RunLedgerEntry()
10. **AP-001** in `tests/unit/interfaces/cli/commands/test_lineage_commands.py:34` - Hard-coded dependency instantiation: LineageNodeRef()
11. **AP-001** in `tests/unit/interfaces/cli/commands/test_lineage_commands.py:38` - Hard-coded dependency instantiation: LineageGraphFragment()
12. **AP-001** in `tests/integration/interfaces/test_cli_run_manifest.py:28` - Hard-coded dependency instantiation: RunID()
13. **AP-001** in `tests/integration/interfaces/test_cli_run_manifest.py:29` - Hard-coded dependency instantiation: RunManifest()
