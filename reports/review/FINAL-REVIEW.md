# BioETL — Full Project Review Report

**Date**: 2026-04-09
**RULES.md Version**: 6.1.0
**Project Version**: 1.0.0
**Total files reviewed**: 5009
**Total LOC reviewed**: 860819

---

## Executive Summary
**Overall Status**: PASS
**Overall Score**: 9.4/10.0

### Key Metrics
| Metric | Value |
|--------|-------|
| Total issues found | 4413 |
| Critical issues | 19 |
| High issues | 4079 |
| Medium issues | 315 |
| Low issues | 0 |
| Sectors reviewed | 8 |

---

## Sector Scores
| Sector | Scope | Files | LOC | Score | Status |
|--------|-------|-------|-----|-------|--------|
| S1 Domain | src/bioetl/domain | 412 | 51796 | 9.6 | PASS |
| S2 Application | src/bioetl/application | 373 | 59542 | 10.0 | PASS |
| S3 Infrastructure | src/bioetl/infrastructure | 397 | 60025 | 10.0 | PASS |
| S4 Composition + Interfaces | src/bioetl/composition, src/bioetl/interfaces | 255 | 32291 | 8.9 | PASS |
| S6 Tests | tests | 1289 | 335179 | 6.7 | WARN |
| S7 Configs | configs | 68 | 10558 | 10.0 | PASS |
| S8 Documentation | docs | 776 | 107624 | 10.0 | PASS |
| S5 Cross-cutting | src/bioetl | 1439 | 203804 | 8.4 | PASS |

---

## Critical Issues (блокируют merge/release)
- **AP-001**: src/bioetl/infrastructure/observability/tracing.py:257 - Hard-coded dependency instantiation: TracerProvider()
- **AP-001**: src/bioetl/infrastructure/observability/anomaly/monitor.py:67 - Hard-coded dependency instantiation: AnomalyDetector()
- **AP-001**: tests/unit/application/composite/test_runner_fsm.py:63 - Hard-coded dependency instantiation: CompositeCheckpointState()
- **AP-001**: tests/unit/application/composite/test_runner_robustness.py:63 - Hard-coded dependency instantiation: CompositeCheckpointState()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:33 - Hard-coded dependency instantiation: SeedResult()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:50 - Hard-coded dependency instantiation: MergeResult()
- **AP-001**: tests/unit/infrastructure/adapters/openalex/test_client_helpers_adapter_mixin.py:21 - Hard-coded dependency instantiation: APIRequestCollector()
- **AP-001**: tests/unit/infrastructure/adapters/openalex/test_request_metadata.py:20 - Hard-coded dependency instantiation: APIRequestCollector()
- **AP-001**: tests/unit/infrastructure/storage/test_silver_writer_merged_mixin.py:21 - Hard-coded dependency instantiation: ArrowDataConverter()
- **AP-001**: tests/unit/interfaces/cli/commands/test_run_manifest_commands.py:31 - Hard-coded dependency instantiation: RunManifest()
- **AP-001**: tests/unit/interfaces/cli/commands/test_run_manifest_commands.py:50 - Hard-coded dependency instantiation: RunLedgerEntry()
- **AP-001**: tests/unit/interfaces/cli/commands/test_lineage_commands.py:34 - Hard-coded dependency instantiation: LineageNodeRef()
- **AP-001**: tests/unit/interfaces/cli/commands/test_lineage_commands.py:38 - Hard-coded dependency instantiation: LineageGraphFragment()
- **AP-001**: tests/integration/interfaces/test_cli_run_manifest.py:28 - Hard-coded dependency instantiation: RunID()
- **AP-001**: tests/integration/interfaces/test_cli_run_manifest.py:29 - Hard-coded dependency instantiation: RunManifest()
- **AP-001**: src/bioetl/infrastructure/export/dq_report_writer.py:59 - Hard-coded dependency instantiation: DQReportSerializer()
- **AP-001**: src/bioetl/infrastructure/observability/tracing.py:257 - Hard-coded dependency instantiation: TracerProvider()
- **AP-001**: src/bioetl/infrastructure/observability/anomaly/monitor.py:67 - Hard-coded dependency instantiation: AnomalyDetector()
- **AP-001**: src/bioetl/infrastructure/validation/contract_validator.py:312 - Hard-coded dependency instantiation: PanderaSilverValidator()
