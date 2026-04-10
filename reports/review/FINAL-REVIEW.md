# BioETL — Full Project Review Report

**Date**: 2026-04-10
**RULES.md Version**: 6.1.0
**Project Version**: 1.0.0
**Total files reviewed**: 5089
**Total LOC reviewed**: 872803

---

## Executive Summary
**Overall Status**: PASS
**Overall Score**: 9.4/10.0

### Key Metrics
| Metric | Value |
|--------|-------|
| Total issues found | 4259 |
| Critical issues | 17 |
| High issues | 4021 |
| Medium issues | 221 |
| Low issues | 0 |
| Sectors reviewed | 8 |

---

## Sector Scores
| Sector | Scope | Files | LOC | Score | Status |
|--------|-------|-------|-----|-------|--------|
| S1 Domain | src/bioetl/domain | 424 | 53314 | 9.6 | PASS |
| S2 Application | src/bioetl/application | 379 | 60570 | 10.0 | PASS |
| S3 Infrastructure | src/bioetl/infrastructure | 401 | 60636 | 10.0 | PASS |
| S4 Composition + Interfaces | src/bioetl/composition, src/bioetl/interfaces | 263 | 32945 | 8.9 | PASS |
| S6 Tests | tests | 1306 | 339061 | 6.6 | WARN |
| S7 Configs | configs | 70 | 10753 | 10.0 | PASS |
| S8 Documentation | docs | 777 | 108013 | 10.0 | PASS |
| S5 Cross-cutting | src/bioetl | 1469 | 207511 | 8.3 | PASS |

---

## Critical Issues (блокируют merge/release)
- **AP-001**: src/bioetl/infrastructure/observability/tracing.py:258 - Hard-coded dependency instantiation: TracerProvider()
- **AP-001**: src/bioetl/infrastructure/observability/anomaly/monitor.py:67 - Hard-coded dependency instantiation: AnomalyDetector()
- **AP-001**: tests/unit/application/composite/test_runner_fsm.py:63 - Hard-coded dependency instantiation: CompositeCheckpointState()
- **AP-001**: tests/unit/application/composite/test_runner_robustness.py:63 - Hard-coded dependency instantiation: CompositeCheckpointState()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:33 - Hard-coded dependency instantiation: SeedResult()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:50 - Hard-coded dependency instantiation: MergeResult()
- **AP-001**: tests/unit/infrastructure/adapters/openalex/test_client_helpers_adapter_mixin.py:21 - Hard-coded dependency instantiation: APIRequestCollector()
- **AP-001**: tests/unit/infrastructure/adapters/openalex/test_request_metadata.py:20 - Hard-coded dependency instantiation: APIRequestCollector()
- **AP-001**: tests/unit/infrastructure/storage/test_silver_writer_merged_mixin.py:21 - Hard-coded dependency instantiation: ArrowDataConverter()
- **AP-001**: tests/unit/interfaces/cli/commands/test_run_manifest_commands.py:32 - Hard-coded dependency instantiation: RunManifest()
- **AP-001**: tests/unit/interfaces/cli/commands/test_run_manifest_commands.py:51 - Hard-coded dependency instantiation: RunLedgerEntry()
- **AP-001**: tests/unit/interfaces/cli/commands/test_lineage_commands.py:34 - Hard-coded dependency instantiation: LineageNodeRef()
- **AP-001**: tests/unit/interfaces/cli/commands/test_lineage_commands.py:38 - Hard-coded dependency instantiation: LineageGraphFragment()
- **AP-001**: tests/integration/interfaces/test_cli_run_manifest.py:28 - Hard-coded dependency instantiation: RunID()
- **AP-001**: tests/integration/interfaces/test_cli_run_manifest.py:29 - Hard-coded dependency instantiation: RunManifest()
- **AP-001**: src/bioetl/infrastructure/export/dq_report_writer.py:59 - Hard-coded dependency instantiation: DQReportSerializer()
- **AP-001**: src/bioetl/infrastructure/validation/contract_validator.py:312 - Hard-coded dependency instantiation: PanderaSilverValidator()
