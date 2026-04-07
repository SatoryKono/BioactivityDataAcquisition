# Consolidated Review — S5: Cross-cutting Concerns
**Date**: 2026-04-07
**Sub-reviews**: 6 agents
**Status**: FAIL
**Consolidated Score**: 6.98

## Sub-review Summary

| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
| S5.1 — Subzone application | 372 | 8.00 | PASS | 0 | 11 |
| S5.2 — Subzone composition | 166 | 9.35 | PASS | 0 | 3 |
| S5.3 — Subzone domain | 412 | 6.40 | WARN | 6 | 3 |
| S5.4 — Subzone infrastructure | 395 | 5.60 | FAIL | 4 | 31 |
| S5.5 — Subzone interfaces | 87 | 7.00 | WARN | 34 | 0 |
| S5.6 — Subzone root | 2 | 10.00 | PASS | 0 | 0 |

## Aggregated Issues

### Critical (MUST fix)
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/domain/exceptions/__init__.py:61`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/domain/exceptions/bounded_context.py:13`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/domain/exceptions/infrastructure/__init__.py:5`
- **ISSUE-2**: Domain imports higher layer in `src/bioetl/domain/exceptions/infrastructure/__init__.py:6`
- **ISSUE-3**: Domain imports higher layer in `src/bioetl/domain/exceptions/infrastructure/__init__.py:15`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/domain/exceptions/infrastructure/_delta.py:7`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/infrastructure/config/domain_config_resolver.py:10`
- **ISSUE-2**: Domain imports higher layer in `src/bioetl/infrastructure/config/domain_config_resolver.py:11`
- **ISSUE-3**: Domain imports higher layer in `src/bioetl/infrastructure/config/domain_config_resolver.py:12`
- **ISSUE-4**: Domain imports higher layer in `src/bioetl/infrastructure/config/domain_config_resolver.py:16`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/composite/command.py:13`
- **ISSUE-2**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/composite/command.py:52`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/composite/execution.py:8`
- **ISSUE-2**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/composite/execution.py:21`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/composite/runtime.py:5`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/composite/support.py:9`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/health/command.py:31`
- **ISSUE-2**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/health/command.py:32`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/maintenance/archive.py:24`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/maintenance/plan.py:24`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/maintenance/vacuum.py:29`
- **ISSUE-2**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/maintenance/vacuum.py:32`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/command.py:70`
- **ISSUE-2**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/command.py:71`
- **ISSUE-3**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/command.py:74`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/command_policy.py:10`
- **ISSUE-2**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/command_policy.py:32`
- **ISSUE-3**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/command_policy.py:35`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/result_flow.py:7`
- **ISSUE-2**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/result_flow.py:10`
- **ISSUE-3**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/result_flow.py:18`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/result_presenter.py:5`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/runtime_helpers.py:8`
- **ISSUE-2**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/runtime_helpers.py:11`
- **ISSUE-3**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/runtime_helpers.py:25`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/service_access.py:8`
- **ISSUE-2**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/service_access.py:19`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/support.py:42`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run_all/command.py:10`
- **ISSUE-2**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run_all/command.py:73`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run_all/command_policy.py:9`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run_all/execution.py:10`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run_all/support.py:12`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/shared/execution_policy.py:16`

### High
- **ISSUE-1**: Hardcoded constructor dependency in `src/bioetl/application/composite/checkpoint/service.py:66`
- **ISSUE-2**: Hardcoded constructor dependency in `src/bioetl/application/composite/checkpoint/service.py:78`
- **ISSUE-1**: Hardcoded constructor dependency in `src/bioetl/application/core/base_transformer/base.py:97`
- **ISSUE-1**: Hardcoded constructor dependency in `src/bioetl/application/core/batch_writer.py:184`
- **ISSUE-2**: Hardcoded constructor dependency in `src/bioetl/application/core/batch_writer.py:191`
- **ISSUE-1**: Hardcoded constructor dependency in `src/bioetl/application/core/idmapping_data_source.py:81`
- **ISSUE-1**: Hardcoded constructor dependency in `src/bioetl/application/core/lifecycle/checkpoint_manager.py:65`
- **ISSUE-1**: Hardcoded constructor dependency in `src/bioetl/application/core/postrun/service.py:96`
- **ISSUE-1**: Hardcoded constructor dependency in `src/bioetl/application/core/runner.py:142`
- **ISSUE-1**: Hardcoded constructor dependency in `src/bioetl/application/observability/observer.py:306`
- **ISSUE-1**: Hardcoded constructor dependency in `src/bioetl/application/pipelines/pubmed/block_definitions.py:264`
- **ISSUE-1**: Direct structlog import outside infrastructure in `src/bioetl/composition/bootstrap_logger.py:25`
- **ISSUE-2**: Hardcoded constructor dependency in `src/bioetl/composition/bootstrap_logger.py:99`
- **ISSUE-1**: Hardcoded constructor dependency in `src/bioetl/composition/factories/pipeline/assembler.py:97`
- **ISSUE-1**: Hardcoded constructor dependency in `src/bioetl/domain/exceptions/network/service.py:190`
- **ISSUE-1**: Hardcoded constructor dependency in `src/bioetl/domain/services/phased_migration_support.py:40`
- **ISSUE-1**: Hardcoded constructor dependency in `src/bioetl/domain/value_objects/compound_ids.py:235`
- **ISSUE-1**: Hardcoded constructor dependency in `src/bioetl/infrastructure/export/dq_report_writer.py:59`
- **ISSUE-1**: Hardcoded constructor dependency in `src/bioetl/infrastructure/observability/anomaly/monitor.py:67`
- **ISSUE-1**: Hardcoded constructor dependency in `src/bioetl/infrastructure/observability/tracing.py:256`
- **ISSUE-2**: Hardcoded constructor dependency in `src/bioetl/infrastructure/observability/tracing.py:257`
- **ISSUE-3**: Hardcoded constructor dependency in `src/bioetl/infrastructure/observability/tracing.py:262`
- **ISSUE-4**: Hardcoded constructor dependency in `src/bioetl/infrastructure/observability/tracing.py:264`
- **ISSUE-1**: Hardcoded constructor dependency in `src/bioetl/infrastructure/observability/unified_logger.py:96`
- **ISSUE-1**: Hardcoded constructor dependency in `src/bioetl/infrastructure/storage/bronze_writer.py:119`
- **ISSUE-2**: Hardcoded constructor dependency in `src/bioetl/infrastructure/storage/bronze_writer.py:120`
- **ISSUE-3**: Hardcoded constructor dependency in `src/bioetl/infrastructure/storage/bronze_writer.py:121`
- **ISSUE-4**: Hardcoded constructor dependency in `src/bioetl/infrastructure/storage/bronze_writer.py:126`
- **ISSUE-5**: Hardcoded constructor dependency in `src/bioetl/infrastructure/storage/bronze_writer.py:130`
- **ISSUE-1**: Hardcoded constructor dependency in `src/bioetl/infrastructure/storage/gold_writer.py:282`
- **ISSUE-2**: Hardcoded constructor dependency in `src/bioetl/infrastructure/storage/gold_writer.py:285`
- **ISSUE-3**: Hardcoded constructor dependency in `src/bioetl/infrastructure/storage/gold_writer.py:286`
- **ISSUE-4**: Hardcoded constructor dependency in `src/bioetl/infrastructure/storage/gold_writer.py:287`
- **ISSUE-5**: Hardcoded constructor dependency in `src/bioetl/infrastructure/storage/gold_writer.py:288`
- **ISSUE-6**: Hardcoded constructor dependency in `src/bioetl/infrastructure/storage/gold_writer.py:292`
- **ISSUE-7**: Hardcoded constructor dependency in `src/bioetl/infrastructure/storage/gold_writer.py:296`
- **ISSUE-1**: Hardcoded constructor dependency in `src/bioetl/infrastructure/storage/silver_writer.py:234`
- **ISSUE-2**: Hardcoded constructor dependency in `src/bioetl/infrastructure/storage/silver_writer.py:237`
- **ISSUE-3**: Hardcoded constructor dependency in `src/bioetl/infrastructure/storage/silver_writer.py:238`
- **ISSUE-4**: Hardcoded constructor dependency in `src/bioetl/infrastructure/storage/silver_writer.py:242`
- **ISSUE-5**: Hardcoded constructor dependency in `src/bioetl/infrastructure/storage/silver_writer.py:243`
- **ISSUE-6**: Hardcoded constructor dependency in `src/bioetl/infrastructure/storage/silver_writer.py:244`
- **ISSUE-7**: Hardcoded constructor dependency in `src/bioetl/infrastructure/storage/silver_writer.py:248`
- **ISSUE-8**: Hardcoded constructor dependency in `src/bioetl/infrastructure/storage/silver_writer.py:252`
- **ISSUE-9**: Hardcoded constructor dependency in `src/bioetl/infrastructure/storage/silver_writer.py:256`
- **ISSUE-10**: Hardcoded constructor dependency in `src/bioetl/infrastructure/storage/silver_writer.py:260`
- **ISSUE-11**: Hardcoded constructor dependency in `src/bioetl/infrastructure/storage/silver_writer.py:264`
- **ISSUE-1**: Hardcoded constructor dependency in `src/bioetl/infrastructure/validation/contract_validator.py:312`

## Cross-subzone Observations
- Standard module boundaries are observed.

## Top 5 Recommendations
1. Adhere to dependency injection guidelines to prevent tight coupling.
