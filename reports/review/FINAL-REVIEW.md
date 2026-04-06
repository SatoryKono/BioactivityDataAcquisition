# BioETL — Full Project Review Report

**Date**: 2026-04-06
**RULES.md Version**: 5.22
**Project Version**: 1.0.0
**Total files reviewed**: 5047
**Total LOC reviewed**: 858873

---

## Executive Summary
**Overall Status**: PASS
**Overall Score**: 9.4/10.0

### Key Metrics
| Metric | Value |
|--------|-------|
| Total issues found | 4376 |
| Critical issues | 139 |
| High issues | 4053 |
| Medium issues | 184 |
| Low issues | 0 |
| Sectors reviewed | 8 |

---

## Sector Scores
| Sector | Scope | Files | LOC | Score | Status |
|--------|-------|-------|-----|-------|--------|
| S1 Domain | src/bioetl/domain | 412 | 51702 | 9.5 | PASS |
| S2 Application | src/bioetl/application | 372 | 59224 | 10.0 | PASS |
| S3 Infrastructure | src/bioetl/infrastructure | 395 | 59785 | 9.3 | PASS |
| S4 Composition + Interfaces | src/bioetl/composition, src/bioetl/interfaces | 252 | 31785 | 8.9 | PASS |
| S6 Tests | tests | 1278 | 333453 | 6.4 | WARN |
| S7 Configs | configs | 67 | 10487 | 10.0 | PASS |
| S8 Documentation | docs | 838 | 109791 | 10.0 | PASS |
| S5 Cross-cutting | src/bioetl | 1433 | 202646 | 10.0 | PASS |

---

## Critical Issues (блокируют merge/release)
- **AP-001**: src/bioetl/infrastructure/storage/delta_reader.py:50 - Hard-coded dependency instantiation: Path()
- **AP-001**: src/bioetl/infrastructure/storage/base_delta_writer.py:191 - Hard-coded dependency instantiation: ArrowDataConverter()
- **AP-001**: src/bioetl/infrastructure/storage/base_delta_writer.py:192 - Hard-coded dependency instantiation: RetentionPolicy()
- **AP-001**: src/bioetl/infrastructure/storage/bronze_writer.py:156 - Hard-coded dependency instantiation: Path()
- **AP-001**: src/bioetl/infrastructure/observability/tracing.py:257 - Hard-coded dependency instantiation: TracerProvider()
- **AP-001**: src/bioetl/infrastructure/observability/anomaly/monitor.py:67 - Hard-coded dependency instantiation: AnomalyDetector()
- **AP-001**: tests/unit/application/composite/test_runner_fsm.py:63 - Hard-coded dependency instantiation: CompositeCheckpointState()
- **AP-001**: tests/unit/application/composite/test_runner_checkpoint_resume.py:107 - Hard-coded dependency instantiation: MagicMock()
- **AP-001**: tests/unit/application/composite/test_runner_required_flag.py:114 - Hard-coded dependency instantiation: MagicMock()
- **AP-001**: tests/unit/application/composite/test_runner.py:99 - Hard-coded dependency instantiation: MagicMock()
- **AP-001**: tests/unit/application/composite/test_runner_robustness.py:63 - Hard-coded dependency instantiation: CompositeCheckpointState()
- **AP-001**: tests/unit/application/composite/test_runner_observability_mixin.py:22 - Hard-coded dependency instantiation: SimpleNamespace()
- **AP-001**: tests/unit/application/composite/test_runner_observability_mixin.py:33 - Hard-coded dependency instantiation: MagicMock()
- **AP-001**: tests/unit/application/core/test_publication_term_data_source.py:27 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/core/test_publication_term_data_source.py:28 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/core/test_publication_term_data_source.py:29 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/core/test_publication_term_data_source.py:30 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/core/test_publication_term_data_source.py:554 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/core/test_publication_term_data_source.py:555 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/core/test_publication_term_data_source.py:556 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/core/test_publication_term_data_source.py:557 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/core/test_runner_execution_flow.py:20 - Hard-coded dependency instantiation: SimpleNamespace()
- **AP-001**: tests/unit/application/core/test_runner_execution_flow.py:21 - Hard-coded dependency instantiation: SimpleNamespace()
- **AP-001**: tests/unit/application/core/test_runner_execution_flow.py:22 - Hard-coded dependency instantiation: SimpleNamespace()
- **AP-001**: tests/unit/application/core/test_runner_execution_flow.py:23 - Hard-coded dependency instantiation: SimpleNamespace()
- **AP-001**: tests/unit/application/core/test_runner_execution_flow.py:27 - Hard-coded dependency instantiation: SimpleNamespace()
- **AP-001**: tests/unit/application/core/test_runner_execution_flow.py:30 - Hard-coded dependency instantiation: SimpleNamespace()
- **AP-001**: tests/unit/application/core/test_runner_execution_flow.py:33 - Hard-coded dependency instantiation: SimpleNamespace()
- **AP-001**: tests/unit/application/core/test_runner_execution_flow.py:34 - Hard-coded dependency instantiation: SimpleNamespace()
- **AP-001**: tests/unit/application/core/test_subcellular_fraction_data_source.py:24 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/core/test_subcellular_fraction_data_source.py:25 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/core/test_subcellular_fraction_data_source.py:26 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/core/test_subcellular_fraction_data_source.py:27 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/core/test_subcellular_fraction_data_source.py:42 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/core/test_subcellular_fraction_data_source.py:43 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/core/test_subcellular_fraction_data_source.py:44 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/core/test_subcellular_fraction_data_source.py:45 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/core/test_batch_executor_dq_mixin.py:63 - Hard-coded dependency instantiation: SimpleNamespace()
- **AP-001**: tests/unit/application/core/test_batch_executor_dq_mixin.py:67 - Hard-coded dependency instantiation: SimpleNamespace()
- **AP-001**: tests/unit/application/core/test_batch_executor_dq_mixin.py:68 - Hard-coded dependency instantiation: SimpleNamespace()
- **AP-001**: tests/unit/application/core/test_batch_executor_recovery.py:25 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/core/test_batch_executor_recovery.py:26 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/core/test_filtered_data_source.py:24 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/core/test_filtered_data_source.py:25 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/core/test_filtered_data_source.py:26 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/core/test_filtered_data_source.py:27 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/core/test_filtered_data_source.py:45 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/core/test_filtered_data_source.py:46 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/core/test_filtered_data_source.py:47 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/core/test_filtered_data_source.py:48 - Hard-coded dependency instantiation: AsyncMock()
