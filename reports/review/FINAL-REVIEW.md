# BioETL — Full Project Review Report

**Date**: 2026-04-25
**RULES.md Version**: 6.1.2
**Project Version**: 1.0.0
**Total files reviewed**: 5830
**Total LOC reviewed**: 1004027

---

## Executive Summary
**Overall Status**: PASS
**Overall Score**: 9.4/10.0

### Key Metrics
| Metric | Value |
|--------|-------|
| Total issues found | 4706 |
| Critical issues | 25 |
| High issues | 4325 |
| Medium issues | 356 |
| Low issues | 0 |
| Sectors reviewed | 8 |

---

## Sector Scores
| Sector | Scope | Files | LOC | Score | Status |
|--------|-------|-------|-----|-------|--------|
| S1 Domain | src/bioetl/domain | 489 | 61852 | 9.6 | PASS |
| S2 Application | src/bioetl/application | 473 | 73426 | 10.0 | PASS |
| S3 Infrastructure | src/bioetl/infrastructure | 446 | 68031 | 9.9 | PASS |
| S4 Composition + Interfaces | src/bioetl/composition, src/bioetl/interfaces | 301 | 38693 | 9.2 | PASS |
| S6 Tests | tests | 1458 | 377930 | 6.3 | WARN |
| S7 Configs | configs | 95 | 13949 | 10.0 | PASS |
| S8 Documentation | docs | 857 | 128073 | 10.0 | PASS |
| S5 Cross-cutting | src/bioetl | 1711 | 242073 | 8.5 | PASS |

---

## Critical Issues (блокируют merge/release)
- **AP-001**: src/bioetl/infrastructure/observability/tracing.py:260 - Hard-coded dependency instantiation: TracerProvider()
- **AP-001**: src/bioetl/infrastructure/observability/anomaly/monitor.py:61 - Hard-coded dependency instantiation: AnomalyDetector()
- **AP-001**: tests/unit/application/composite/runner_test_support.py:47 - Hard-coded dependency instantiation: CompositeCheckpointState()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_support_mixin.py:92 - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_merge_stage_mixin.py:79 - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_stage_start_flow.py:24 - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_stage_mixin.py:95 - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_stage_enrichment_mixin.py:82 - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_stage_support_mixin.py:92 - Hard-coded dependency instantiation: CompositeLifecycleObserverService()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:34 - Hard-coded dependency instantiation: SeedResult()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:51 - Hard-coded dependency instantiation: MergeResult()
- **AP-001**: tests/unit/infrastructure/adapters/openalex/test_client_helpers_adapter_mixin.py:23 - Hard-coded dependency instantiation: APIRequestCollector()
- **AP-001**: tests/unit/infrastructure/adapters/openalex/test_request_metadata.py:20 - Hard-coded dependency instantiation: APIRequestCollector()
- **AP-001**: tests/unit/infrastructure/storage/test_silver_writer_merged_mixin.py:23 - Hard-coded dependency instantiation: ArrowDataConverter()
- **AP-001**: tests/unit/interfaces/cli/commands/test_run_manifest_commands.py:43 - Hard-coded dependency instantiation: RunManifest()
- **AP-001**: tests/unit/interfaces/cli/commands/test_run_manifest_commands.py:64 - Hard-coded dependency instantiation: RunLedgerEntry()
- **AP-001**: tests/unit/interfaces/cli/commands/test_lineage_commands.py:34 - Hard-coded dependency instantiation: LineageNodeRef()
- **AP-001**: tests/unit/interfaces/cli/commands/test_lineage_commands.py:38 - Hard-coded dependency instantiation: LineageGraphFragment()
- **AP-001**: tests/integration/interfaces/test_cli_run_manifest.py:28 - Hard-coded dependency instantiation: RunID()
- **AP-001**: tests/integration/interfaces/test_cli_run_manifest.py:29 - Hard-coded dependency instantiation: RunManifest()
- **AP-001**: tests/integration/ci/test_reproducibility_contract_suite.py:130 - Hard-coded dependency instantiation: RunID()
- **AP-001**: src/bioetl/infrastructure/export/dq_report_writer.py:59 - Hard-coded dependency instantiation: DQReportSerializer()
- **AP-001**: src/bioetl/infrastructure/observability/tracing.py:260 - Hard-coded dependency instantiation: TracerProvider()
- **AP-001**: src/bioetl/infrastructure/observability/anomaly/monitor.py:61 - Hard-coded dependency instantiation: AnomalyDetector()
- **AP-001**: src/bioetl/infrastructure/validation/contract_validator.py:313 - Hard-coded dependency instantiation: PanderaSilverValidator()
