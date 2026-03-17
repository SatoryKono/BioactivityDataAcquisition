# Consolidated Review — S2: Application
**Date**: 2026-03-17
**Sub-reviews**: 16 agents
**Status**: WARN
**Consolidated Score**: 7.0
## Sub-review Summary
| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
| S2.1 — Subzone_1 | 17 | 7.0 | WARN | 0 | 15 |
| S2.2 — Subzone_2 | 15 | 7.0 | WARN | 0 | 15 |
| S2.3 — Subzone_3 | 19 | 7.0 | WARN | 0 | 17 |
| S2.4 — Subzone_4 | 18 | 7.0 | WARN | 0 | 17 |
| S2.5 — Subzone_5 | 16 | 7.0 | WARN | 0 | 16 |
| S2.6 — Subzone_6 | 14 | 7.0 | WARN | 0 | 14 |
| S2.7 — Subzone_7 | 16 | 6.9 | WARN | 1 | 15 |
| S2.8 — Subzone_8 | 13 | 7.0 | WARN | 0 | 13 |
| S2.9 — Subzone_9 | 16 | 6.9 | WARN | 1 | 14 |
| S2.10 — Subzone_10 | 15 | 7.0 | WARN | 0 | 12 |
| S2.11 — Subzone_11 | 20 | 7.0 | WARN | 0 | 17 |
| S2.12 — Subzone_12 | 16 | 7.0 | WARN | 0 | 14 |
| S2.13 — Subzone_13 | 15 | 7.0 | WARN | 0 | 13 |
| S2.14 — Subzone_14 | 21 | 7.0 | WARN | 0 | 18 |
| S2.15 — Subzone_15 | 15 | 7.0 | WARN | 0 | 13 |
| S2.16 — Subzone_16 | 4 | 8.8 | PASS | 0 | 4 |
## Aggregated Issues
### Critical (MUST fix)
- **TEST-005**: `src/bioetl/application/services/pipeline_debug_service.py:143` - Test logic in production code
- **TEST-005**: `src/bioetl/application/composite/checkpoint/service.py:83` - Test logic in production code
### High
- **ADR-014**: `src/bioetl/application/composite/dependency_coordinator.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/conflict_resolver.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/_preflight_rules.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/cross_validator.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/protocols.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/merger_output_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/fsm_helper.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/join_key_resolution.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/dependency_result_mapper.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/merger_orchestration.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/coordinator.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/coordinator_result_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/join_execution.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/aggregator.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/column_renamer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/merger_post_join.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/merger.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/merger_input_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/deduplication.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/dependency_joiner.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/_preflight_types.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/_preflight_reporting.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/cross_validator_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/coalesce_policy.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/join_planner.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/join_planner_delegation_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/runtime_models.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/dependency_key_resolvers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/merger_metrics_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/key_extractor.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/dependency_join_support.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/column_orderer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/column_orderer_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/merger_collaborators.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/_preflight_orchestration.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/dependency_progress_tracker.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/merger_io_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/column_priority_orderer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/preflight_validator.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/join_planner_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/generic.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/observability/span_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/observability/observer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/observability/observer_context_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/observability/observer_event_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/batch_extraction_loop_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/batch_memory_manager.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/dict_transformers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/protocols.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/batch_transformer_orchestration.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/batch_executor_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/publication_term_data_source.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/batch_execution_run_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/batch_metrics.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/base.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/record_processor.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/batch_transformer_state.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/batch_progress_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/publication_aliases.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/base_transformer_helpers_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/pipeline_services.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/batch_execution_lifecycle.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/batch_execution_state_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/batch_transformer_quarantine.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/_filtered_data_source_mixins.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/quarantine_manager.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/_data_source_mixins.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/batch_transformer_finalization.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/batch_transformer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/batch_executor_loop_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/publication_term_extraction_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/filtered_data_source.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/batch_tracing.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/batch_writer_columns_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/batch_executor_dq_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/field_specs.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/config.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/batch_transformer_streaming.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/batch_transformer_attempts.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/entity_id.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/batch_executor.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/batch_writer_tracing_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/publication_term_filtering_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/batch_writer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/idmapping_data_source.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/batch_processing_service_mixins.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/batch_processing_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/runner.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/subcellular_fraction_data_source.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/base_transformer_dependency_helpers_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/batch_checkpoint_recovery_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/batch_writer_io_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/data_quality_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/export_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/metadata_assemblers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/pipeline_runner_models.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/lock_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/config_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/bronze_cleanup_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/pipeline_runner_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/pipeline_run_context_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/dq_report_models.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/metrics_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/pipeline_debug_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/pipeline_run_lifecycle_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/health_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/export_models.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/cli_run_orchestration_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/shutdown_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/dq_report_generation_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/metadata_coordinator.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/vacuum_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/medallion_maintenance_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/quarantine_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/medallion_lifecycle.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/metadata_assemblers_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/medallion_types.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/checkpoint_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/pipeline_run_execution_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/dq_report_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/runner_pkg/runner_stage_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/runner_pkg/runner_merge_stage_types.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/runner_pkg/runner_support_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/runner_pkg/runner_stage_types.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/runner_pkg/runner_merge_stage_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/runner_pkg/runner_observability_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/runner_pkg/runner_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/runner_pkg/runner_stage_enrichment_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/runner_pkg/runner_stage_support_types.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/runner_pkg/runner_stage_support_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/runner_pkg/runner_support_types.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/runner_pkg/runner_stage_enrichment_types.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/runner_pkg/runner.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/runner_pkg/runner_constants.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/runner_pkg/runner_models.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/checkpoint/service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/composite/checkpoint/state.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/semanticscholar/_author_extractors.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/semanticscholar/_page_parsing.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/semanticscholar/transformer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/semanticscholar/extractors.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/common/base_publication_transformer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/common/extractors.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/crossref/author_extractors.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/crossref/transformer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/crossref/_business_data_builder.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/crossref/extractors.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/crossref/reference_extractors.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/openalex/_extractors_publication_fields.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/openalex/transformer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/openalex/_extractors_topics_grants.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/openalex/_extractors_authors.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/openalex/extractors.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/openalex/_extractors_common.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/pubmed/transformer_dates_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/pubmed/transformer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/pubmed/xml_parser.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/pubmed/transformer_authors_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/uniprot/transformer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/uniprot/transformer_business_data_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/uniprot/idmapping_transformer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/chembl/base_chembl_transformer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/chembl/cell_line_transformer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/chembl/target_transformer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/chembl/tissue_transformer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/chembl/assay_parameters_transformer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/chembl/molecule_transformer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/chembl/protein_class_transformer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/chembl/_pipelines.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/chembl/assay_transformer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/chembl/publication_term_transformer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/chembl/target_component_transformer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/chembl/compound_record_transformer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/chembl/publication_similarity_transformer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/chembl/subcellular_fraction_transformer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/chembl/activity_transformer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/chembl/publication_transformer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/pubchem/transformer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/pubmed/extractors/publication.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/pubmed/extractors/classification.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/pubmed/extractors/author.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/pubmed/extractors/base.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/pubmed/extractors/identifier.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/pubmed/extractors/identifier_types.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/pubmed/extractors/date.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/pubmed/extractors/abstract.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/uniprot/extractors/_crossref_structured.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/uniprot/extractors/_comment_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/uniprot/extractors/taxonomy.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/uniprot/extractors/genes.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/uniprot/extractors/_feature_wrappers_mixin.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/uniprot/extractors/_comment_facets.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/uniprot/extractors/comments.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/uniprot/extractors/features.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/uniprot/extractors/crossrefs.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/uniprot/extractors/_crossref_common.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/uniprot/extractors/extractor_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/pipelines/uniprot/extractors/_crossref_go.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/base_transformer/errors.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/base_transformer/base.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/base_transformer/types.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/base_transformer/contract_policy.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/postrun/service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/postrun/dq_report_orchestrator.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/postrun/cleanup_orchestrator.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/postrun/compact_orchestrator.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/postrun/metadata_version_resolver.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/lifecycle/heartbeat.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/lifecycle/lock_manager.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/lifecycle/checkpoint_manager.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/lifecycle/shutdown.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/lifecycle/cleanup_service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/preflight/medallion_validator.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/preflight/service.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/core/preflight/health_aggregator.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/dq/bronze_analyzer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/dq/_checks_basic.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/dq/silver_statistics.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/dq/dq_report_builders.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/dq/gold_analyzer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/dq/silver_check_executor.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/dq/silver_threshold.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/dq/silver_statistics_helpers.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/dq/_checks_business.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/dq/silver_analyzer.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/dq/_checks_statistical.py:1` - Missing from __future__ import annotations
- **ADR-014**: `src/bioetl/application/services/dq/_checks_integrity.py:1` - Missing from __future__ import annotations
## Cross-subzone Observations
Dynamically aggregated reports successfully verified dependencies.
## Top 5 Recommendations
1. Fix any cross-layer boundary violations.
2. Adopt strict typing across all zones.