# BioETL — Full Project Review Report

**Date**: 2026-05-16
**RULES.md Version**: unknown
**Project Version**: 1.0.0
**Total files reviewed**: 6352
**Total LOC reviewed**: 1143706

---

## Executive Summary
**Overall Status**: PASS
**Overall Score**: 9.3/10.0

### Key Metrics
| Metric | Value |
|--------|-------|
| Total issues found | 4877 |
| Critical issues | 20 |
| High issues | 4486 |
| Medium issues | 371 |
| Low issues | 0 |
| Sectors reviewed | 8 |

---

## Sector Scores
| Sector | Scope | Files | LOC | Score | Status |
|--------|-------|-------|-----|-------|--------|
| S1 Domain | src/bioetl/domain | 541 | 70312 | 9.6 | PASS |
| S2 Application | src/bioetl/application | 526 | 85898 | 10.0 | PASS |
| S3 Infrastructure | src/bioetl/infrastructure | 464 | 73202 | 9.7 | PASS |
| S4 Composition + Interfaces | src/bioetl/composition, src/bioetl/interfaces | 340 | 48286 | 8.9 | PASS |
| S6 Tests | tests | 1694 | 441515 | 6.3 | WARN |
| S7 Configs | configs | 151 | 20854 | 10.0 | PASS |
| S8 Documentation | docs | 763 | 125901 | 10.0 | PASS |
| S5 Cross-cutting | src/bioetl | 1873 | 277738 | 8.4 | PASS |

---

## Critical Issues (блокируют merge/release)
- **AP-001**: src/bioetl/infrastructure/observability/tracing.py:260 - Hard-coded dependency instantiation: TracerProvider()
- **AP-001**: src/bioetl/infrastructure/observability/anomaly/monitor.py:61 - Hard-coded dependency instantiation: AnomalyDetector()
- **AP-001**: tests/unit/application/composite/runner_test_support.py:52 - Hard-coded dependency instantiation: CompositeCheckpointState()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_merge_stage_mixin.py:79 - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_stage_start_flow.py:24 - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:34 - Hard-coded dependency instantiation: SeedResult()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:51 - Hard-coded dependency instantiation: MergeResult()
- **AP-001**: tests/unit/infrastructure/adapters/openalex/test_client_helpers_adapter_mixin.py:28 - Hard-coded dependency instantiation: APIRequestCollector()
- **AP-001**: tests/unit/infrastructure/adapters/openalex/test_request_metadata.py:21 - Hard-coded dependency instantiation: APIRequestCollector()
- **AP-001**: tests/unit/infrastructure/storage/test_silver_writer_merged_mixin.py:25 - Hard-coded dependency instantiation: ArrowDataConverter()
- **AP-001**: tests/unit/interfaces/cli/commands/test_run_manifest_commands.py:45 - Hard-coded dependency instantiation: RunManifest()
- **AP-001**: tests/unit/interfaces/cli/commands/test_run_manifest_commands.py:66 - Hard-coded dependency instantiation: RunLedgerEntry()
- **AP-001**: tests/unit/interfaces/cli/commands/test_lineage_commands.py:34 - Hard-coded dependency instantiation: LineageNodeRef()
- **AP-001**: tests/unit/interfaces/cli/commands/test_lineage_commands.py:38 - Hard-coded dependency instantiation: LineageGraphFragment()
- **AP-001**: tests/integration/interfaces/test_cli_run_manifest.py:29 - Hard-coded dependency instantiation: RunID()
- **AP-001**: tests/integration/interfaces/test_cli_run_manifest.py:30 - Hard-coded dependency instantiation: RunManifest()
- **AP-001**: tests/integration/ci/reproducibility_contract_support.py:72 - Hard-coded dependency instantiation: RunID()
- **AP-001**: src/bioetl/infrastructure/export/dq_report_writer.py:59 - Hard-coded dependency instantiation: DQReportSerializer()
- **AP-001**: src/bioetl/infrastructure/observability/tracing.py:260 - Hard-coded dependency instantiation: TracerProvider()
- **AP-001**: src/bioetl/infrastructure/observability/anomaly/monitor.py:61 - Hard-coded dependency instantiation: AnomalyDetector()
