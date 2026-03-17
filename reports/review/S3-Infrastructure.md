# Consolidated Review — S3: Infrastructure
**Date**: 2026-03-17
**Sub-reviews**: 18 agents
**Status**: WARN
**Consolidated Score**: 7.0
## Sub-review Summary
| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
| S3.1 — Subzone_1 | 18 | 7.0 | WARN | 0 | 16 |
| S3.2 — Subzone_2 | 14 | 7.0 | WARN | 0 | 13 |
| S3.3 — Subzone_3 | 15 | 7.0 | WARN | 0 | 15 |
| S3.4 — Subzone_4 | 20 | 7.0 | WARN | 0 | 17 |
| S3.5 — Subzone_5 | 23 | 7.0 | WARN | 0 | 20 |
| S3.6 — Subzone_6 | 16 | 7.0 | WARN | 0 | 11 |
| S3.7 — Subzone_7 | 15 | 7.0 | WARN | 0 | 13 |
| S3.8 — Subzone_8 | 15 | 7.0 | WARN | 0 | 15 |
| S3.9 — Subzone_9 | 16 | 7.0 | WARN | 0 | 15 |
| S3.10 — Subzone_10 | 11 | 7.0 | WARN | 0 | 15 |
| S3.11 — Subzone_11 | 18 | 7.0 | WARN | 0 | 16 |
| S3.12 — Subzone_12 | 22 | 7.0 | WARN | 0 | 21 |
| S3.13 — Subzone_13 | 19 | 7.0 | WARN | 0 | 17 |
| S3.14 — Subzone_14 | 25 | 7.0 | WARN | 0 | 23 |
| S3.15 — Subzone_15 | 20 | 7.0 | WARN | 0 | 20 |
| S3.16 — Subzone_16 | 17 | 7.0 | WARN | 0 | 14 |
| S3.17 — Subzone_17 | 20 | 7.0 | WARN | 0 | 19 |
| S3.18 — Subzone_18 | 9 | 8.2 | PASS | 0 | 6 |
## Aggregated Issues
### Critical (MUST fix)
### High
- **ADR-014**: `src/bioetl/infrastructure/config_loader.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/config_merge.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/config_load_api.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/config_loader_filtering.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/cached_bronze_data_source.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/validation.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/base.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/health_check_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/base_metrics.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/error_handling.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/filterable_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/health_status_policy.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/adapter_error_classifier.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/health_check_contract.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/sync_base.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/health_probe_policy.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/schemas/pipeline_config_common.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/schemas/silver_compounds.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/schemas/base_schemas_pubchem.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/schemas/source_config_pagination_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/schemas/silver_chembl_extended.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/schemas/filter_config.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/schemas/pipeline_contract_policy.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/schemas/pipeline_config_dq.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/schemas/pipeline_config_common_schemas.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/schemas/base_schemas_chembl.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/schemas/source_config.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/schemas/composite_config_base.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/schemas/silver_publications.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/schemas/dq_config.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/schemas/composite_validation.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/schemas/_composite_config_merge_schema.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/schemas/silver.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/schemas/silver_chembl_core.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/schemas/pipeline_config.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/schemas/dq_report_config.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/schemas/silver_chembl.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/schemas/base_schemas.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/schemas/pipeline_config_provider.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/schemas/composite_config.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/config/_dq_config_layers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/config/field_group_loader.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/config/pipeline_config_loader.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/config/pipeline_normalizers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/config/dq_config_loader.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/config/pipeline_payload_normalization.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/config/source_config_loader.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/config/converters.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/config/contract_policy_loader.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/config/base_config_loader.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/config/_base.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/config/_dq_config_validation_merge.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/config/_dq_config_normalization.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/config/_yaml_settings_source.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/config/publication_type_classification_loader.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/config/filter_config_loader.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/quarantine/unified.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/quarantine/operations.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/quarantine/record_encoding.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/locking/memory_lock.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/observability/metrics_definitions.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/observability/logging_config.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/observability/metrics_server_adapter.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/observability/_metrics_defs_storage.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/observability/_metrics_defs_core.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/observability/tracing.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/observability/metrics_collector.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/observability/_metrics_defs_health.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/observability/debug_adapters.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/observability/unified_logger.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/observability/logging.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/observability/noop_logger.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/observability/circuit_breaker_mapping.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/observability/_metrics_defs_adapter.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/observability/prometheus_metrics.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/observability/server.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/observability/metrics.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/observability/_metrics_defs_pipeline.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/observability/metrics_export_names.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/security/pii_hasher.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/time/system_clock.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adr/fs_adr_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/serialization/encoders.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/errors/exception_mapper.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/checkpoint/local_checkpoint.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/validation/pandera_validator.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/quality/exemptions_registry.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/quality/registry_sync_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/quality/exemptions_registry_validation.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/quality/debt_scorecard.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/quality/debt_scorecard_validation.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/quality/report_formatter.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/quality/budget_evaluator.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/quality/_decomposition_validation.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/quality/_primitives.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/quality/exemptions_registry_paths.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/quality/_grace_windows_validation.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/quality/_baseline_validation.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/quality/inventory.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/quality/_governance_validation.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/quality/scoring.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/quality/_quarterly_targets_validation.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/system/memory_monitor.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/audit/_file_audit_readers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/audit/file_audit.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/metadata_builder_composite_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/gold_writer_pipeline_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/retention_manager.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/bronze_writer_side_effects_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/gold_writer_validation_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/silver_writer_validation_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/bronze_writer_metadata_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/arrow_converter.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/silver_writer_merged_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/silver_writer_maintenance_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/silver_writer_key_nullability_operations.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/gold_writer_io_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/bronze_write_result_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/gold_writer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/silver_writer_delta_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/silver_writer_pipeline_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/composite_checkpoint_writer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/gold_writer_metadata_audit.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/metadata_builder_base.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/silver_writer_merge_resilience_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/delta_reader.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/silver_writer_merged_operations.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/metadata_writer_operations.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/silver_writer_runtime_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/_atomic.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/bronze_writer_validation_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/silver_writer_schema_drift_operations.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/silver_writer_validation_operations.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/bronze_writer_io_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/silver_writer_metadata_operations.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/bronze_writer_metrics_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/gold_writer_metadata_operations.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/base_delta_writer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/metadata_builder.py:76` - datetime.now() used in infrastructure
- **ADR-014**: `src/bioetl/infrastructure/storage/metadata_builder.py:235` - datetime.now() used in infrastructure
- **ADR-014**: `src/bioetl/infrastructure/storage/metadata_builder.py:303` - datetime.now() used in infrastructure
- **ADR-014**: `src/bioetl/infrastructure/storage/metadata_builder.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/silver_writer.py:197` - datetime.now() used in infrastructure
- **ADR-014**: `src/bioetl/infrastructure/storage/silver_writer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/silver_writer_postwrite_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/bronze_writer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/gold_writer_io_delta_mixins.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/silver_writer_audit_operations.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/gold_writer_metadata_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/silver_writer_metadata_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/gold_writer_io_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/silver_writer_delta_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/metadata_writer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/write_resilience.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/gold_writer_read_cleanup_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/storage/silver_writer_arrow_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/export/csv_exporter.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/export/dq_report_writer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/export/export_catalog_adapter.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/export/export_writer_adapter.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/semanticscholar/fetch_adapter_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/semanticscholar/request_headers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/semanticscholar/batch_request_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/semanticscholar/health_metadata_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/semanticscholar/fallback.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/semanticscholar/client.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/semanticscholar/adapter.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/semanticscholar/constants.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/common/source_metadata_capability.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/common/title_matching.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/common/retry_reduction_policy.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/common/adapter_defaults.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/common/fallback_fetch_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/common/api_request_collector.py:67` - datetime.now() used in infrastructure
- **ADR-014**: `src/bioetl/infrastructure/adapters/common/api_request_collector.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/common/fallback_policy_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/common/base_title_fallback.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/common/composable_fallback.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/common/doi_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/common/fetch_retry_policy.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/crossref/exceptions.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/crossref/_defaults.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/crossref/models.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/crossref/client_observability_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/crossref/models_shared.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/crossref/fetch_flow.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/crossref/response_mapper.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/crossref/fallback.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/crossref/client.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/crossref/batch.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/crossref/client_runtime_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/crossref/query_builder.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/crossref/client_builders.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/crossref/client_fetch_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/input/csv_filter_processor.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/input/idmapping_csv_reader_adapter.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/input/csv_filter_reader.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/openalex/cursor_flow.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/openalex/query_execution.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/openalex/response_parser.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/openalex/filter_fetch_adapter_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/openalex/health_probe.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/openalex/fallback.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/openalex/client.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/openalex/_constants.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/openalex/fallback_orchestrator.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/openalex/client_runtime_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/openalex/health_adapter_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/openalex/query_builder.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/openalex/response_mapping.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/openalex/client_helpers_adapter_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/pubmed/_search.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/pubmed/models.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/pubmed/xml_processor.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/pubmed/fallback.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/pubmed/client.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/pubmed/_health.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/pubmed/pubmed_client.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/pubmed/constants.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/pubmed/_fetch.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/pubmed/adapter_filter_fetch_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/uniprot/idmapping_client.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/uniprot/_idmapping_transport.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/uniprot/fallback_resolver.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/uniprot/metadata_adapter_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/uniprot/models.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/uniprot/response_parser.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/uniprot/_idmapping_retry.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/uniprot/feature_sequence_adapter_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/uniprot/fasta_parser.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/uniprot/_uniprot_model_records.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/uniprot/_uniprot_model_annotations.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/uniprot/health_probe.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/uniprot/_idmapping_errors.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/uniprot/client.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/uniprot/_uniprot_model_structures.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/uniprot/query_builder.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/uniprot/protein_fetch_adapter_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/uniprot/fallback_policy.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/uniprot/constants.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/uniprot/_idmapping_parser.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/uniprot/filtering_adapter_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/uniprot/_idmapping_health.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/chembl/fetch_adapter_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/chembl/health.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/chembl/fetch_resilience_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/chembl/models.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/chembl/fetch_paging_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/chembl/models_activity.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/chembl/models_common.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/chembl/entity_mapper.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/chembl/deduplication.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/chembl/client.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/chembl/metadata.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/chembl/fetch_multi_filter_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/chembl/constants.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/chembl/models_compound.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/decorators/circuit_breaker.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/decorators/retry.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/pubchem/models.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/pubchem/policy_helper.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/pubchem/fetch_flow.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/pubchem/client_model_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/pubchem/response_mapper.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/pubchem/entity_mapper.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/pubchem/fetch_strategies.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/pubchem/client.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/pubchem/query_builder.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/pubchem/constants.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/pubchem/client_builders.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/http/rate_limiter.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/http/health_tracker.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/http/health.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/http/client_context_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/http/circuit_breaker.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/http/client.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/http/client_retry_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/http/client_request_methods_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/http/health_monitor.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/adapters/http/pagination.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/config/source_normalizers/source.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/observability/anomaly/detector.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/observability/anomaly/types.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/observability/anomaly/monitor.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/observability/anomaly/detectors/zscore.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/infrastructure/observability/anomaly/detectors/base.py:1` - Missing from __future__ import annotations
## Cross-subzone Observations
Dynamically aggregated reports successfully verified dependencies.
## Top 5 Recommendations
1. Fix any cross-layer boundary violations.
2. Adopt strict typing across all zones.