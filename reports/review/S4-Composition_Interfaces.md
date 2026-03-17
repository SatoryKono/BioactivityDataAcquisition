# Consolidated Review — S4: Composition Interfaces
**Date**: 2026-03-17
**Sub-reviews**: 9 agents
**Status**: WARN
**Consolidated Score**: 7.0
## Sub-review Summary
| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
| S4.1 — Subzone_1 | 17 | 6.8 | WARN | 0 | 16 |
| S4.2 — Subzone_2 | 22 | 7.0 | WARN | 0 | 17 |
| S4.3 — Subzone_3 | 17 | 7.0 | WARN | 0 | 15 |
| S4.4 — Subzone_4 | 22 | 7.0 | WARN | 0 | 20 |
| S4.5 — Subzone_5 | 22 | 7.0 | WARN | 0 | 20 |
| S4.6 — Subzone_6 | 27 | 7.0 | WARN | 0 | 21 |
| S4.7 — Subzone_7 | 18 | 7.0 | WARN | 0 | 17 |
| S4.8 — Subzone_8 | 15 | 7.0 | WARN | 0 | 15 |
| S4.9 — Subzone_9 | 2 | 9.4 | PASS | 0 | 2 |
## Aggregated Issues
### Critical (MUST fix)
### High
- **ADR-014**: `src/bioetl/composition/registry.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/_pipeline_execution.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap_contexts.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/_services.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/types.py:1` - Missing from __future__ import annotations
- **AP-002**: `src/bioetl/composition/bootstrap_logger.py:25` - Direct structlog import outside infrastructure layer
- **ADR-014**: `src/bioetl/composition/bootstrap_logger.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/observability.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/_resource_management.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/entrypoints.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/builders.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/providers/_config_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/providers/provider_registry.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/providers/registration_bio.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/providers/_models.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/providers/_store.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/providers/factory_loader.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/providers/registration.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/providers/loader.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/providers/registration_biblio.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/providers/decorators.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/providers/_creation.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/transformer_dependencies.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/transformer_factory.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/_observability_wiring.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/batch_id_generator.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/runtime_builders/observability_builder.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/runtime_builders/runner_builder.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/runtime_builders/inputs_resolver.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/services/versioning.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/dq/context_resolver.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/dq/factory.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/pipeline/transformer_dependencies.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/pipeline/runner_assembly.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/pipeline/assembler.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/pipeline/factory_method_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/pipeline/registry.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/pipeline/construction.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/pipeline/_creation_wiring.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/pipeline/contract_validator.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/pipeline/config_types.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/pipeline/postrun_assembly.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/pipeline/runner.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/pipeline/configs.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/datasource/http_client.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/datasource/data_source_factory.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/datasource/crossref.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/datasource/adapter_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/storage/maintenance_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/storage/write_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/storage/merged_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/storage/_silver.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/storage/storage_factory.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/storage/_resilience.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/storage/_gold.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/storage/_bronze.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/storage/_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/storage/adapter.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/storage/health_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/storage/clear_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/storage/factory.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/services/pipeline_processing.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/services/common_service_wiring.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/services/builder.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/services/port_factories.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/services/runtime_managers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/services/bundle.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/services/callbacks.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/services/factory.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/factories/services/pipeline_builder.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/cli/health.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/cli/lock.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/cli/adr.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/cli/metrics.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/cli/config.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/cli/storage.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/cli/noop.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/cli/checkpoint.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/runtime/assembly.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/runtime/config_loader.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/runtime/pipeline.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/runtime/runner_assembly.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/runtime/composite.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/runtime/classification_init.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/runtime/metrics_bootstrap.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/runtime/observability_bundle.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/runtime/composite_dq_loader.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/runtime/runtime_basics.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/runtime/logger_bootstrap.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/runtime/pipeline_runner_service_bootstrap.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/runtime/runner_factory_builder_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/runtime/observability.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/runtime/dq_bootstrap.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/runtime/composite_support_service_builders.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/runtime/composite_support_services_factory.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/runtime/composite_bootstrap_builders.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/runtime/runner.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/runtime/composite_support_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/runtime/tracing_bootstrap.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/runtime/composite_filter_extraction_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/assembly/storage.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/composition/bootstrap/assembly/checkpoint.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/observability.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/formatters.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/exit_codes.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/registry_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/main.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/http/health_server_http_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/http/types.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/http/health_server_routing_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/http/health_server.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/http/health_server_state_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/health_rendering.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/cleanup.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/run_composite.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/health.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/archive.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/quarantine_rendering.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/maintenance.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/metrics_server_integration.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/execution_policy.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/run_command_policy.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/lock.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/run_all_execution.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/export_support.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/run_composite_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/adr.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/quarantine_execution.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/health_server_integration.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/run_all.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/quarantine_support.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/config.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/vacuum.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/run_result_presenter.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/run_all_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/run.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/quarantine.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/checkpoint.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/run_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/run_composite_runtime.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/run_all_command_policy.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/debug.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/interfaces/cli/commands/export.py:1` - Missing from __future__ import annotations
## Cross-subzone Observations
Dynamically aggregated reports successfully verified dependencies.
## Top 5 Recommendations
1. Fix any cross-layer boundary violations.
2. Adopt strict typing across all zones.