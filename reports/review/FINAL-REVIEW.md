# BioETL — Full Project Review Report

**Date**: 2026-04-06
**RULES.md Version**: 5.22
**Project Version**: 1.0.0
**Total files reviewed**: 4967
**Total LOC reviewed**: 853932

---

## Executive Summary
**Overall Status**: PASS
**Overall Score**: 9.2/10.0

### Key Metrics
| Metric | Value |
|--------|-------|
| Total issues found | 4528 |
| Critical issues | 151 |
| High issues | 4064 |
| Medium issues | 313 |
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
| S8 Documentation | docs | 758 | 104850 | 10.0 | PASS |
| S5 Cross-cutting | src/bioetl | 1433 | 202646 | 8.1 | PASS |

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
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_support_mixin.py:72 - Hard-coded dependency instantiation: SimpleNamespace()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_support_mixin.py:77 - Hard-coded dependency instantiation: MagicMock()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_support_mixin.py:80 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_support_mixin.py:82 - Hard-coded dependency instantiation: MagicMock()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_support_mixin.py:85 - Hard-coded dependency instantiation: MagicMock()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_merge_stage_mixin.py:58 - Hard-coded dependency instantiation: SimpleNamespace()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_merge_stage_mixin.py:71 - Hard-coded dependency instantiation: SimpleNamespace()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_merge_stage_mixin.py:72 - Hard-coded dependency instantiation: MagicMock()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_merge_stage_mixin.py:74 - Hard-coded dependency instantiation: MagicMock()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_merge_stage_mixin.py:75 - Hard-coded dependency instantiation: MagicMock()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_merge_stage_mixin.py:82 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_stage_mixin.py:83 - Hard-coded dependency instantiation: SimpleNamespace()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_stage_mixin.py:89 - Hard-coded dependency instantiation: MagicMock()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_stage_mixin.py:91 - Hard-coded dependency instantiation: MagicMock()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_stage_mixin.py:92 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_stage_mixin.py:107 - Hard-coded dependency instantiation: MagicMock()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_stage_mixin.py:109 - Hard-coded dependency instantiation: MagicMock()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_stage_enrichment_mixin.py:75 - Hard-coded dependency instantiation: SimpleNamespace()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_stage_enrichment_mixin.py:76 - Hard-coded dependency instantiation: MagicMock()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_stage_enrichment_mixin.py:78 - Hard-coded dependency instantiation: MagicMock()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_stage_enrichment_mixin.py:80 - Hard-coded dependency instantiation: MagicMock()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_stage_enrichment_mixin.py:81 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_stage_enrichment_mixin.py:82 - Hard-coded dependency instantiation: MagicMock()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_stage_support_mixin.py:65 - Hard-coded dependency instantiation: SimpleNamespace()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_stage_support_mixin.py:70 - Hard-coded dependency instantiation: MagicMock()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_stage_support_mixin.py:72 - Hard-coded dependency instantiation: MagicMock()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_stage_support_mixin.py:73 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_stage_support_mixin.py:76 - Hard-coded dependency instantiation: MagicMock()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_stage_support_mixin.py:77 - Hard-coded dependency instantiation: MagicMock()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_stage_support_mixin.py:80 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_completion_helpers.py:62 - Hard-coded dependency instantiation: SimpleNamespace()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_completion_helpers.py:63 - Hard-coded dependency instantiation: SimpleNamespace()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_completion_helpers.py:66 - Hard-coded dependency instantiation: MagicMock()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_completion_helpers.py:69 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_completion_helpers.py:70 - Hard-coded dependency instantiation: AsyncMock()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_observability_mixin.py:33 - Hard-coded dependency instantiation: SimpleNamespace()
- **AP-001**: tests/unit/application/composite/runner_pkg/test_runner_observability_mixin.py:44 - Hard-coded dependency instantiation: MagicMock()
