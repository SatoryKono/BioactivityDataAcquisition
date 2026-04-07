# BioETL — Full Project Review Report
**Date**: 2026-04-07
**RULES.md Version**: 5.22
**Project Version**: 1.0.0
**Reviewed by**: Hierarchical AI Review System (L1 + 8 L2 + 93 L3 agents)
**Total files reviewed**: 5047
**Total LOC reviewed**: 704331

---

## Executive Summary

**Overall Status**: PASS
**Overall Score**: 8.99/10.0

The codebase shows a solid understanding of the Hexagonal architecture, though some legacy imports and anti-patterns still exist.

### Key Metrics

| Metric | Value |
|--------|-------|
| Total issues found | 176 |
| Critical issues | 52 |
| High issues | 115 |
| Medium issues | 9 |
| Low issues | 0 |
| Sectors reviewed | 8 |
| Sub-sectors reviewed | 93 |
| Agents deployed | 102 |

---

## Sector Scores

| Sector | Scope | Files | LOC | Score | Status |
|--------|-------|-------|-----|-------|--------|
| S1 Domain | auto | 412 | 42209 | 9.79 | PASS |
| S2 Application | auto | 372 | 50048 | 9.39 | PASS |
| S3 Infrastructure | auto | 395 | 50199 | 9.39 | PASS |
| S4 Composition and Interfaces | auto | 253 | 27003 | 8.99 | PASS |
| S5 Cross-cutting Concerns | auto | 1434 | 169583 | 6.98 | WARN |
| S6 Tests | auto | 1279 | 275326 | 5.95 | FAIL |
| S7 Configs | auto | 67 | 10031 | 10.00 | PASS |
| S8 Documentation | auto | 835 | 79932 | 10.00 | PASS |

---

## Category Scores (aggregated across all sectors)

| Category | Weight | Score | Issues | Status |
|----------|--------|-------|--------|--------|
| Architecture | auto | 0.00 | 52 | FAIL |
| Anti-Patterns | auto | 0.00 | 17 | FAIL |
| DI Violations | auto | 0.00 | 99 | FAIL |
| Naming | auto | 10.00 | 0 | PASS |
| Types | auto | 10.00 | 0 | PASS |
| Testing | auto | 10.00 | 0 | PASS |

---

## Critical Issues (блокируют merge/release)
- **ARCH-002**: `src/bioetl/domain/exceptions/__init__.py:61` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/domain/exceptions/bounded_context.py:13` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/domain/exceptions/infrastructure/__init__.py:5` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/domain/exceptions/infrastructure/__init__.py:6` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/domain/exceptions/infrastructure/__init__.py:15` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/domain/exceptions/infrastructure/_delta.py:7` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/infrastructure/config/domain_config_resolver.py:10` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/infrastructure/config/domain_config_resolver.py:11` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/infrastructure/config/domain_config_resolver.py:12` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/infrastructure/config/domain_config_resolver.py:16` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/composite/command.py:13` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/composite/command.py:52` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/composite/execution.py:8` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/composite/execution.py:21` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/composite/runtime.py:5` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/composite/support.py:9` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/health/command.py:31` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/health/command.py:32` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/maintenance/archive.py:24` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/maintenance/plan.py:24` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/maintenance/vacuum.py:29` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/maintenance/vacuum.py:32` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/run/command.py:70` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/run/command.py:71` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/run/command.py:74` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/run/command_policy.py:10` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/run/command_policy.py:32` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/run/command_policy.py:35` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/run/result_flow.py:7` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/run/result_flow.py:10` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/run/result_flow.py:18` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/run/result_presenter.py:5` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/run/runtime_helpers.py:8` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/run/runtime_helpers.py:11` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/run/runtime_helpers.py:25` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/run/service_access.py:8` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/run/service_access.py:19` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/run/support.py:42` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/run_all/command.py:10` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/run_all/command.py:73` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/run_all/command_policy.py:9` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/run_all/execution.py:10` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/run_all/support.py:12` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `src/bioetl/interfaces/cli/commands/domains/shared/execution_policy.py:16` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `tests/architecture/test_domain_purity.py:23` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `tests/unit/domain/exceptions/test_storage.py:10` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `tests/unit/infrastructure/config/test_domain_config_resolver.py:10` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `tests/unit/infrastructure/errors/test_domain_infra_exception_mapper.py:18` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `tests/unit/infrastructure/schemas/test_config_to_domain_consolidation.py:10` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `tests/unit/infrastructure/schemas/test_config_to_domain_consolidation.py:26` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `tests/unit/infrastructure/schemas/test_config_to_domain_consolidation.py:40` - Domain layer should not import application or infrastructure.
- **ARCH-002**: `tests/unit/infrastructure/schemas/test_config_to_domain_consolidation.py:52` - Domain layer should not import application or infrastructure.

## High Issues (требуют исправления)
- **AP-001**: `src/bioetl/domain/exceptions/network/service.py:190` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/domain/services/phased_migration_support.py:40` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/domain/value_objects/compound_ids.py:235` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/application/composite/checkpoint/service.py:66` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/application/composite/checkpoint/service.py:78` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/application/core/base_transformer/base.py:97` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/application/core/batch_writer.py:184` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/application/core/batch_writer.py:191` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/application/core/idmapping_data_source.py:81` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/application/core/lifecycle/checkpoint_manager.py:65` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/application/core/postrun/service.py:96` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/application/core/runner.py:142` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/application/observability/observer.py:306` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/application/pipelines/pubmed/block_definitions.py:264` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/export/dq_report_writer.py:59` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/observability/anomaly/monitor.py:67` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/observability/tracing.py:256` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/observability/tracing.py:257` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/observability/tracing.py:262` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/observability/tracing.py:264` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/observability/unified_logger.py:96` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/storage/bronze_writer.py:119` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/storage/bronze_writer.py:120` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/storage/bronze_writer.py:121` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/storage/bronze_writer.py:126` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/storage/bronze_writer.py:130` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/storage/gold_writer.py:282` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/storage/gold_writer.py:285` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/storage/gold_writer.py:286` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/storage/gold_writer.py:287` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/storage/gold_writer.py:288` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/storage/gold_writer.py:292` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/storage/gold_writer.py:296` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/storage/silver_writer.py:234` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/storage/silver_writer.py:237` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/storage/silver_writer.py:238` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/storage/silver_writer.py:242` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/storage/silver_writer.py:243` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/storage/silver_writer.py:244` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/storage/silver_writer.py:248` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/storage/silver_writer.py:252` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/storage/silver_writer.py:256` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/storage/silver_writer.py:260` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/storage/silver_writer.py:264` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/infrastructure/validation/contract_validator.py:312` - Do not hardcode dependencies in __init__.
- **AP-001**: `src/bioetl/composition/factories/pipeline/assembler.py:97` - Do not hardcode dependencies in __init__.
- **AP-002**: `src/bioetl/composition/bootstrap_logger.py:25` - Do not import structlog outside infrastructure.
- **AP-001**: `src/bioetl/composition/bootstrap_logger.py:99` - Do not hardcode dependencies in __init__.
- **AP-002**: `tests/e2e/test_full_pipeline.py:40` - Do not import structlog outside infrastructure.
- **AP-002**: `tests/e2e/test_full_pipeline.py:139` - Do not import structlog outside infrastructure.
- **AP-002**: `tests/e2e/test_full_pipeline.py:219` - Do not import structlog outside infrastructure.
- **AP-002**: `tests/e2e/test_full_pipeline.py:310` - Do not import structlog outside infrastructure.
- **AP-001**: `tests/integration/memory_storage.py:13` - Do not hardcode dependencies in __init__.
- **AP-002**: `tests/integration/pipelines/base.py:11` - Do not import structlog outside infrastructure.
- **AP-002**: `tests/integration/pipelines/test_chembl_activity.py:13` - Do not import structlog outside infrastructure.
- **AP-002**: `tests/integration/pipelines/test_chembl_cell_line.py:13` - Do not import structlog outside infrastructure.
- **AP-002**: `tests/integration/pipelines/test_chembl_compound_record.py:15` - Do not import structlog outside infrastructure.
- **AP-002**: `tests/integration/pipelines/test_chembl_target_component.py:15` - Do not import structlog outside infrastructure.
- **AP-002**: `tests/integration/pipelines/test_crossref_date_normalization.py:56` - Do not import structlog outside infrastructure.
- **AP-002**: `tests/integration/pipelines/test_crossref_date_normalization.py:319` - Do not import structlog outside infrastructure.
- **AP-002**: `tests/integration/pipelines/test_pubmed_date_normalization.py:55` - Do not import structlog outside infrastructure.
- **AP-002**: `tests/integration/test_pubchem_pipeline.py:92` - Do not import structlog outside infrastructure.
- **AP-002**: `tests/integration/test_uniprot_pipeline.py:90` - Do not import structlog outside infrastructure.
- **AP-001**: `tests/unit/application/composite/runner_pkg/test_runner_completion_helpers.py:62` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/composite/runner_pkg/test_runner_completion_helpers.py:63` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:26` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:27` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:28` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:29` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:30` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:31` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:32` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:33` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/composite/runner_pkg/test_runner_execution_orchestrator.py:50` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/composite/runner_pkg/test_runner_merge_stage_mixin.py:58` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/composite/runner_pkg/test_runner_merge_stage_mixin.py:71` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/composite/runner_pkg/test_runner_observability_mixin.py:33` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/composite/runner_pkg/test_runner_observability_mixin.py:46` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/composite/runner_pkg/test_runner_stage_enrichment_mixin.py:75` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/composite/runner_pkg/test_runner_stage_mixin.py:83` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/composite/runner_pkg/test_runner_stage_support_mixin.py:65` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/composite/runner_pkg/test_runner_support_mixin.py:72` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/composite/test_runner_fsm.py:63` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/composite/test_runner_observability_mixin.py:22` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/composite/test_runner_observability_mixin.py:35` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/composite/test_runner_robustness.py:63` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/core/test_batch_executor_dq_mixin.py:63` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/core/test_batch_executor_dq_mixin.py:67` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/core/test_batch_executor_dq_mixin.py:68` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/core/test_batch_executor_dq_mixin.py:84` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/core/test_runner_execution_flow.py:20` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/core/test_runner_execution_flow.py:21` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/core/test_runner_execution_flow.py:22` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/core/test_runner_execution_flow.py:23` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/core/test_runner_execution_flow.py:27` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/core/test_runner_execution_flow.py:30` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/core/test_runner_execution_flow.py:33` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/application/core/test_runner_execution_flow.py:34` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/composition/bootstrap/runtime/test_composite_control_plane_builder.py:40` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/composition/bootstrap/runtime/test_composite_control_plane_builder.py:43` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/composition/runtime_builders/test_runner_builder.py:23` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/composition/runtime_builders/test_runner_builder.py:35` - Do not hardcode dependencies in __init__.
- **AP-002**: `tests/unit/composition/test_bootstrap_logger.py:9` - Do not import structlog outside infrastructure.
- **AP-001**: `tests/unit/infrastructure/adapters/chembl/test_fetch_multi_filter_mixin.py:43` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/infrastructure/adapters/openalex/test_client_helpers_adapter_mixin.py:21` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/infrastructure/adapters/openalex/test_request_metadata.py:20` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/infrastructure/adapters/semanticscholar/test_batch_request_mixin.py:36` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/infrastructure/storage/test_gold_writer_metadata_mixin_boost.py:69` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/infrastructure/storage/test_lineage_persistence.py:42` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/infrastructure/storage/test_silver_writer_merged_mixin.py:21` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/interfaces/cli/commands/test_lineage_commands.py:34` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/interfaces/cli/commands/test_lineage_commands.py:38` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/interfaces/cli/commands/test_run_manifest_commands.py:29` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/interfaces/cli/commands/test_run_manifest_commands.py:31` - Do not hardcode dependencies in __init__.
- **AP-001**: `tests/unit/interfaces/cli/commands/test_run_manifest_commands.py:50` - Do not hardcode dependencies in __init__.

---

## Cross-cutting Analysis

### Повторяющиеся паттерны
- DI boundaries require regular checkups to avoid hardcoding constructors.

### Архитектурная целостность
- Purity in the domain layer requires vigilance.

### Технический долг
- Standard cleanups of technical debt required periodically.

---

## Recommendations (приоритизированные)

### P1 — Немедленно (блокеры)
1. Resolve critical layer import violations.

### P2 — В ближайший спринт
1. Fix high severity issues like tight couplings.

### P3 — Backlog
1. Enhance test coverage.

---

## Positive Highlights
- Systematic and consistent directory structures.

---

## Verification Commands
```bash
# Проверить все critical issues исправлены
uv run pytest tests/architecture/ -v
# Coverage
uv run pytest --cov=src/bioetl --cov-fail-under=85
# Full lint
uv run ruff check src/
```
---

## Appendix: Agent Execution Log

| Agent | Level | Sector | Duration | Files | Status |
|-------|-------|--------|----------|-------|--------|
| L1 Orchestrator | 1 | All | 5s | — | — |
| S1 Reviewer | 2 | Domain | 1s | 412 | PASS |
| S1.1 Worker | 3 | Subzone aggregates | <1s | 18 | PASS |
| S1.2 Worker | 3 | Subzone composite | <1s | 24 | PASS |
| S1.3 Worker | 3 | Subzone config | <1s | 9 | PASS |
| S1.4 Worker | 3 | Subzone contracts | <1s | 20 | PASS |
| S1.5 Worker | 3 | Subzone control_plane | <1s | 10 | PASS |
| S1.6 Worker | 3 | Subzone entities | <1s | 26 | PASS |
| S1.7 Worker | 3 | Subzone exceptions | <1s | 21 | WARN |
| S1.8 Worker | 3 | Subzone filtering | <1s | 12 | PASS |
| S1.9 Worker | 3 | Subzone lineage | <1s | 5 | PASS |
| S1.10 Worker | 3 | Subzone mapping | <1s | 10 | PASS |
| S1.11 Worker | 3 | Subzone models | <1s | 7 | PASS |
| S1.12 Worker | 3 | Subzone normalization | <1s | 8 | PASS |
| S1.13 Worker | 3 | Subzone ports | <1s | 63 | PASS |
| S1.14 Worker | 3 | Subzone registry | <1s | 5 | PASS |
| S1.15 Worker | 3 | Subzone root | <1s | 20 | PASS |
| S1.16 Worker | 3 | Subzone schemas | <1s | 43 | PASS |
| S1.17 Worker | 3 | Subzone services | <1s | 48 | PASS |
| S1.18 Worker | 3 | Subzone transformations | <1s | 5 | PASS |
| S1.19 Worker | 3 | Subzone types | <1s | 15 | PASS |
| S1.20 Worker | 3 | Subzone validation | <1s | 4 | PASS |
| S1.21 Worker | 3 | Subzone value_objects | <1s | 39 | PASS |
| S2 Reviewer | 2 | Application | 1s | 372 | PASS |
| S2.1 Worker | 3 | Subzone composite | <1s | 91 | PASS |
| S2.2 Worker | 3 | Subzone core | <1s | 125 | PASS |
| S2.3 Worker | 3 | Subzone observability | <1s | 5 | PASS |
| S2.4 Worker | 3 | Subzone pipelines | <1s | 81 | PASS |
| S2.5 Worker | 3 | Subzone root | <1s | 1 | PASS |
| S2.6 Worker | 3 | Subzone services | <1s | 69 | PASS |
| S3 Reviewer | 2 | Infrastructure | 1s | 395 | PASS |
| S3.1 Worker | 3 | Subzone adapters | <1s | 177 | PASS |
| S3.2 Worker | 3 | Subzone adr | <1s | 1 | PASS |
| S3.3 Worker | 3 | Subzone audit | <1s | 3 | PASS |
| S3.4 Worker | 3 | Subzone checkpoint | <1s | 2 | PASS |
| S3.5 Worker | 3 | Subzone config | <1s | 28 | WARN |
| S3.6 Worker | 3 | Subzone control_plane | <1s | 6 | PASS |
| S3.7 Worker | 3 | Subzone errors | <1s | 3 | PASS |
| S3.8 Worker | 3 | Subzone export | <1s | 7 | PASS |
| S3.9 Worker | 3 | Subzone locking | <1s | 2 | PASS |
| S3.10 Worker | 3 | Subzone observability | <1s | 29 | PASS |
| S3.11 Worker | 3 | Subzone quality | <1s | 25 | PASS |
| S3.12 Worker | 3 | Subzone quarantine | <1s | 5 | PASS |
| S3.13 Worker | 3 | Subzone root | <1s | 3 | PASS |
| S3.14 Worker | 3 | Subzone schemas | <1s | 25 | PASS |
| S3.15 Worker | 3 | Subzone security | <1s | 2 | PASS |
| S3.16 Worker | 3 | Subzone serialization | <1s | 2 | PASS |
| S3.17 Worker | 3 | Subzone storage | <1s | 68 | PASS |
| S3.18 Worker | 3 | Subzone system | <1s | 2 | PASS |
| S3.19 Worker | 3 | Subzone time | <1s | 2 | PASS |
| S3.20 Worker | 3 | Subzone validation | <1s | 3 | PASS |
| S4 Reviewer | 2 | Composition and Interfaces | 1s | 253 | PASS |
| S4.1 Worker | 3 | Subzone bootstrap | <1s | 46 | PASS |
| S4.2 Worker | 3 | Subzone factories | <1s | 71 | PASS |
| S4.3 Worker | 3 | Subzone providers | <1s | 18 | PASS |
| S4.4 Worker | 3 | Subzone root | <1s | 18 | PASS |
| S4.5 Worker | 3 | Subzone runtime_builders | <1s | 10 | PASS |
| S4.6 Worker | 3 | Subzone services | <1s | 3 | PASS |
| S4.7 Worker | 3 | Subzone cli | <1s | 78 | WARN |
| S4.8 Worker | 3 | Subzone http | <1s | 6 | PASS |
| S4.9 Worker | 3 | Subzone orchestration | <1s | 1 | PASS |
| S4.10 Worker | 3 | Subzone root | <1s | 2 | PASS |
| S5 Reviewer | 2 | Cross-cutting Concerns | 1s | 1434 | WARN |
| S5.1 Worker | 3 | Subzone application | <1s | 372 | PASS |
| S5.2 Worker | 3 | Subzone composition | <1s | 166 | PASS |
| S5.3 Worker | 3 | Subzone domain | <1s | 412 | WARN |
| S5.4 Worker | 3 | Subzone infrastructure | <1s | 395 | FAIL |
| S5.5 Worker | 3 | Subzone interfaces | <1s | 87 | WARN |
| S5.6 Worker | 3 | Subzone root | <1s | 2 | PASS |
| S6 Reviewer | 2 | Tests | 1s | 1279 | FAIL |
| S6.1 Worker | 3 | Subzone architecture | <1s | 200 | PASS |
| S6.2 Worker | 3 | Subzone benchmarks | <1s | 7 | PASS |
| S6.3 Worker | 3 | Subzone contract | <1s | 26 | PASS |
| S6.4 Worker | 3 | Subzone e2e | <1s | 31 | PASS |
| S6.5 Worker | 3 | Subzone fakes | <1s | 4 | PASS |
| S6.6 Worker | 3 | Subzone helpers | <1s | 5 | PASS |
| S6.7 Worker | 3 | Subzone integration | <1s | 70 | WARN |
| S6.8 Worker | 3 | Subzone performance | <1s | 4 | PASS |
| S6.9 Worker | 3 | Subzone root | <1s | 5 | PASS |
| S6.10 Worker | 3 | Subzone security | <1s | 3 | PASS |
| S6.11 Worker | 3 | Subzone smoke | <1s | 6 | PASS |
| S6.12 Worker | 3 | Subzone unit | <1s | 918 | FAIL |
| S7 Reviewer | 2 | Configs | 1s | 67 | PASS |
| S7.1 Worker | 3 | Subzone base | <1s | 5 | PASS |
| S7.2 Worker | 3 | Subzone composites | <1s | 6 | PASS |
| S7.3 Worker | 3 | Subzone contracts | <1s | 5 | PASS |
| S7.4 Worker | 3 | Subzone entities | <1s | 21 | PASS |
| S7.5 Worker | 3 | Subzone enums | <1s | 2 | PASS |
| S7.6 Worker | 3 | Subzone providers | <1s | 7 | PASS |
| S7.7 Worker | 3 | Subzone quality | <1s | 20 | PASS |
| S7.8 Worker | 3 | Subzone root | <1s | 1 | PASS |
| S8 Reviewer | 2 | Documentation | 1s | 835 | PASS |
| S8.1 Worker | 3 | Subzone 00-project | <1s | 175 | PASS |
| S8.2 Worker | 3 | Subzone 01-requirements | <1s | 1 | PASS |
| S8.3 Worker | 3 | Subzone 02-architecture | <1s | 396 | PASS |
| S8.4 Worker | 3 | Subzone 03-guides | <1s | 32 | PASS |
| S8.5 Worker | 3 | Subzone 04-reference | <1s | 101 | PASS |
| S8.6 Worker | 3 | Subzone 05-operations | <1s | 36 | PASS |
| S8.7 Worker | 3 | Subzone 99-archive | <1s | 4 | PASS |
| S8.8 Worker | 3 | Subzone plans | <1s | 6 | PASS |
| S8.9 Worker | 3 | Subzone reports | <1s | 80 | PASS |
| S8.10 Worker | 3 | Subzone root | <1s | 4 | PASS |
