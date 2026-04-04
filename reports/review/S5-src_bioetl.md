# Code Review Report — S5: Cross-cutting Concerns
**Date**: 2026-04-04
**Scope**: src/bioetl
**Files reviewed**: 1429
**Total LOC**: 166494
**Status**: WARN
**Score**: 6.0/10.0
---
## Summary
| Category | Issues | CRIT | HIGH | MED | LOW | Score |
|----------|--------|------|------|-----|-----|-------|
| Architecture | 20 | 0 | 20 | 0 | 0 | 0.0 |
| Anti-Patterns | 0 | 0 | 0 | 0 | 0 | 10.0 |
| DI Violations | 0 | 0 | 0 | 0 | 0 | 10.0 |
| Naming | 304 | 0 | 0 | 0 | 304 | 0.0 |
| Types | 0 | 0 | 0 | 0 | 0 | 10.0 |
| Testing | 0 | 0 | 0 | 0 | 0 | 10.0 |
| **TOTAL** | **324** | **0** | **20** | **0** | **304** | **6.0** |
## High Issues
### DI-005: Factory class ProviderHttpClientFactoryProtocol outside composition/tests
- **File**: `src/bioetl/composition/providers/_registration_contracts.py`

### DI-005: Factory class ProviderAdapterFactoryProtocol outside composition/tests
- **File**: `src/bioetl/composition/providers/_registration_contracts.py`

### DI-005: Factory class BaseServicesFactory outside composition/tests
- **File**: `src/bioetl/composition/factories/services/factory.py`

### DI-005: Factory class RunnerFactory outside composition/tests
- **File**: `src/bioetl/composition/factories/pipeline/runner.py`

### DI-005: Factory class GenericPipelineFactory outside composition/tests
- **File**: `src/bioetl/composition/factories/pipeline/assembler.py`

### DI-005: Factory class _PipelineFactoryContext outside composition/tests
- **File**: `src/bioetl/composition/factories/pipeline/factory_method_helpers.py`

### DI-005: Factory class _BuildFactoryServicesRequest outside composition/tests
- **File**: `src/bioetl/composition/factories/pipeline/factory_method_helpers.py`

### DI-005: Factory class PipelineFactoryConfig outside composition/tests
- **File**: `src/bioetl/composition/factories/pipeline/config_types.py`

### DI-005: Factory class _PipelineFactoryRegistrationState outside composition/tests
- **File**: `src/bioetl/composition/factories/pipeline/registry.py`

### DI-005: Factory class RunContextFactory outside composition/tests
- **File**: `src/bioetl/composition/factories/pipeline/run_context_factory.py`

### DI-005: Factory class DataSourceFactory outside composition/tests
- **File**: `src/bioetl/composition/factories/datasource/data_source_factory.py`

### DI-005: Factory class AdapterHelpersFactory outside composition/tests
- **File**: `src/bioetl/composition/factories/datasource/adapter_helpers.py`

### DI-005: Factory class HttpClientFactory outside composition/tests
- **File**: `src/bioetl/composition/factories/datasource/http_client.py`

### DI-005: Factory class StorageFactory outside composition/tests
- **File**: `src/bioetl/composition/factories/storage/factory.py`

### DI-005: Factory class DQServicesFactory outside composition/tests
- **File**: `src/bioetl/composition/factories/dq/factory.py`

### DI-005: Factory class RunnerFactoryBuilderService outside composition/tests
- **File**: `src/bioetl/composition/bootstrap/runtime/runner_factory_builder_service.py`

### DI-005: Factory class CompositeSupportServicesFactory outside composition/tests
- **File**: `src/bioetl/composition/bootstrap/runtime/composite_support_services_factory.py`

### DI-005: Factory class DataSourceFactoryPort outside composition/tests
- **File**: `src/bioetl/domain/ports/data_source.py`

### DI-005: Factory class RunnerFactoryPort outside composition/tests
- **File**: `src/bioetl/domain/ports/runtime/runner.py`

### DI-005: Factory class PipelineFactoryPort outside composition/tests
- **File**: `src/bioetl/domain/ports/runtime/runner.py`

## Low Issues
### NAME-001: Class _SupportsDefaultRegistry not PascalCase
- **File**: `src/bioetl/composition/providers/_default_registry.py`

### NAME-001: Class _SupportsProviderStore not PascalCase
- **File**: `src/bioetl/composition/providers/_default_registry.py`

### NAME-001: Class _SupportsProviderRegistryStore not PascalCase
- **File**: `src/bioetl/composition/providers/_default_registry.py`

### NAME-001: Class _LoggerBindableObservability not PascalCase
- **File**: `src/bioetl/composition/runtime_builders/runner_builder.py`

### NAME-001: Class _PaginationConfigLike not PascalCase
- **File**: `src/bioetl/composition/runtime_builders/inputs_resolver.py`

### NAME-001: Class _SourceConfigLike not PascalCase
- **File**: `src/bioetl/composition/runtime_builders/inputs_resolver.py`

### NAME-001: Class _ManifestControlPlaneRefs not PascalCase
- **File**: `src/bioetl/composition/runtime_builders/run_manifest_builder.py`

### NAME-001: Class _PipelineFactoryContext not PascalCase
- **File**: `src/bioetl/composition/factories/pipeline/factory_method_helpers.py`

### NAME-001: Class _BuildFactoryServicesRequest not PascalCase
- **File**: `src/bioetl/composition/factories/pipeline/factory_method_helpers.py`

### NAME-001: Class _ServiceBundleDeps not PascalCase
- **File**: `src/bioetl/composition/factories/pipeline/_creation_wiring.py`

### NAME-001: Class _BuildPipelineServicesFn not PascalCase
- **File**: `src/bioetl/composition/factories/pipeline/_creation_wiring.py`

### NAME-001: Class _PipelineCreationRequest not PascalCase
- **File**: `src/bioetl/composition/factories/pipeline/_creation_wiring.py`

### NAME-001: Class _PipelineCreationInputs not PascalCase
- **File**: `src/bioetl/composition/factories/pipeline/_creation_wiring.py`

### NAME-001: Class _SchemaBuilder not PascalCase
- **File**: `src/bioetl/composition/factories/pipeline/construction_types.py`

### NAME-001: Class _PipelineFactoryRegistrationState not PascalCase
- **File**: `src/bioetl/composition/factories/pipeline/registry.py`

### NAME-001: Class _RunnerAssemblyContext not PascalCase
- **File**: `src/bioetl/composition/factories/pipeline/runner_assembly.py`

### NAME-001: Class _SilverMergedWriteProtocol not PascalCase
- **File**: `src/bioetl/composition/factories/storage/merged_mixin.py`

### NAME-001: Class _ModelDumpable not PascalCase
- **File**: `src/bioetl/composition/factories/dq/context_resolver.py`

### NAME-001: Class _BootstrapRuntimeBasics not PascalCase
- **File**: `src/bioetl/composition/bootstrap/runtime/runner_bootstrap_wiring.py`

### NAME-001: Class _BootstrapRunnerFactories not PascalCase
- **File**: `src/bioetl/composition/bootstrap/runtime/runner_bootstrap_wiring.py`

### NAME-001: Class _CompositeRunnerServiceInputs not PascalCase
- **File**: `src/bioetl/composition/bootstrap/runtime/runner_assembly.py`

### NAME-001: Class _CompositeBootstrapPlan not PascalCase
- **File**: `src/bioetl/composition/bootstrap/runtime/composite.py`

### NAME-001: Class _RunLedgerDefaultsHost not PascalCase
- **File**: `src/bioetl/application/services/_run_ledger_diagnostic_support.py`

### NAME-001: Class _MedallionMaintenanceMixin not PascalCase
- **File**: `src/bioetl/application/services/medallion_maintenance_mixin.py`

### NAME-001: Class _PipelineRunLifecycleProtocol not PascalCase
- **File**: `src/bioetl/application/services/pipeline_run_lifecycle_service.py`

### NAME-001: Class _ValueCarrier not PascalCase
- **File**: `src/bioetl/application/services/data_quality_service.py`

### NAME-001: Class _DQAnomalyLike not PascalCase
- **File**: `src/bioetl/application/services/data_quality_service.py`

### NAME-001: Class _MedallionClearMixin not PascalCase
- **File**: `src/bioetl/application/services/medallion_lifecycle.py`

### NAME-001: Class _MedallionRunLifecycleMixin not PascalCase
- **File**: `src/bioetl/application/services/medallion_lifecycle.py`

### NAME-001: Class _LegacySilverReadable not PascalCase
- **File**: `src/bioetl/application/composite/merger_input_mixin.py`

### NAME-001: Class _MergeInputLoaderMixin not PascalCase
- **File**: `src/bioetl/application/composite/merger_input_mixin.py`

### NAME-001: Class _PipelineIdentity not PascalCase
- **File**: `src/bioetl/application/composite/join_planner_helpers.py`

### NAME-001: Class _PreparedEnricherJoinContext not PascalCase
- **File**: `src/bioetl/application/composite/join_planner.py`

### NAME-001: Class _EnricherExecutionContext not PascalCase
- **File**: `src/bioetl/application/composite/coordinator.py`

### NAME-001: Class _PreparedSeedDataframe not PascalCase
- **File**: `src/bioetl/application/composite/merger_input_runtime.py`

### NAME-001: Class _BoundLegacySilverReader not PascalCase
- **File**: `src/bioetl/application/composite/merger_input_runtime.py`

### NAME-001: Class _EnricherValidationResult not PascalCase
- **File**: `src/bioetl/application/composite/cross_validator.py`

### NAME-001: Class _CoordinatorPlanningHost not PascalCase
- **File**: `src/bioetl/application/composite/coordinator_planning.py`

### NAME-001: Class _ObserverContextManagerMixin not PascalCase
- **File**: `src/bioetl/application/observability/observer_context_mixin.py`

### NAME-001: Class _ObserverLifecycleEmissionMixin not PascalCase
- **File**: `src/bioetl/application/observability/observer.py`

### NAME-001: Class _ObserverEventMixin not PascalCase
- **File**: `src/bioetl/application/observability/observer_event_mixin.py`

### NAME-001: Class _HasWrappedDataSource not PascalCase
- **File**: `src/bioetl/application/core/_data_source_mixins.py`

### NAME-001: Class _SourceMetadataDelegationMixin not PascalCase
- **File**: `src/bioetl/application/core/_data_source_mixins.py`

### NAME-001: Class _WrappedDataSourceDelegationMixin not PascalCase
- **File**: `src/bioetl/application/core/_data_source_mixins.py`

### NAME-001: Class _CurrentSpanStarter not PascalCase
- **File**: `src/bioetl/application/core/_span_helpers.py`

### NAME-001: Class _TracingProvider not PascalCase
- **File**: `src/bioetl/application/core/_span_helpers.py`

### NAME-001: Class _ClosableSpan not PascalCase
- **File**: `src/bioetl/application/core/_span_helpers.py`

### NAME-001: Class _TransformerExecutionOwner not PascalCase
- **File**: `src/bioetl/application/core/base_transformer_execution_mixin.py`

### NAME-001: Class _BaseTransformerExecutionMixin not PascalCase
- **File**: `src/bioetl/application/core/base_transformer_execution_mixin.py`

### NAME-001: Class _FilteredDataSourceStateMixin not PascalCase
- **File**: `src/bioetl/application/core/_filtered_data_source_mixins.py`

### NAME-001: Class _FilteredDataSourceLifecycleMixin not PascalCase
- **File**: `src/bioetl/application/core/_filtered_data_source_mixins.py`

### NAME-001: Class _FilteredDataSourceFetchMixin not PascalCase
- **File**: `src/bioetl/application/core/_filtered_data_source_mixins.py`

### NAME-001: Class _FilteredDataSourceState not PascalCase
- **File**: `src/bioetl/application/core/_filtered_data_source_support.py`

### NAME-001: Class _PipelineRunnerFlowHostProtocol not PascalCase
- **File**: `src/bioetl/application/core/runner_flow.py`

### NAME-001: Class _IDMappingFetchState not PascalCase
- **File**: `src/bioetl/application/core/_idmapping_fetch_support.py`

### NAME-001: Class _PipelineRunnerExecutionHostProtocol not PascalCase
- **File**: `src/bioetl/application/core/runner_execution_flow.py`

### NAME-001: Class _TrackedStage not PascalCase
- **File**: `src/bioetl/application/core/runner_execution_flow.py`

### NAME-001: Class _ExecutionCycleContext not PascalCase
- **File**: `src/bioetl/application/core/runner_execution_flow.py`

### NAME-001: Class _TargetEntityFetchWrapper not PascalCase
- **File**: `src/bioetl/application/core/_target_data_source_mixins.py`

### NAME-001: Class _TargetEntityFetchDelegationMixin not PascalCase
- **File**: `src/bioetl/application/core/_target_data_source_mixins.py`

### NAME-001: Class _FilterableTargetWrapper not PascalCase
- **File**: `src/bioetl/application/core/_target_data_source_mixins.py`

### NAME-001: Class _FilterableTargetDelegatingWrapper not PascalCase
- **File**: `src/bioetl/application/core/_target_data_source_mixins.py`

### NAME-001: Class _FallbackFilterableTargetWrapper not PascalCase
- **File**: `src/bioetl/application/core/_target_data_source_mixins.py`

### NAME-001: Class _FilterableTargetDelegationMixin not PascalCase
- **File**: `src/bioetl/application/core/_target_data_source_mixins.py`

### NAME-001: Class _FallbackFilterableTargetFetchMixin not PascalCase
- **File**: `src/bioetl/application/core/_target_data_source_mixins.py`

### NAME-001: Class _TransformerDependencyOwner not PascalCase
- **File**: `src/bioetl/application/core/base_transformer_dependency_helpers_mixin.py`

### NAME-001: Class _BaseTransformerDependencyHelpersMixin not PascalCase
- **File**: `src/bioetl/application/core/base_transformer_dependency_helpers_mixin.py`

### NAME-001: Class _BaseTransformerRecordHelpersMixin not PascalCase
- **File**: `src/bioetl/application/core/base_transformer_helpers_mixin.py`

### NAME-001: Class _BatchProgressReporterPort not PascalCase
- **File**: `src/bioetl/application/core/batch_executor_loop_progress.py`

### NAME-001: Class _BatchProgressSnapshot not PascalCase
- **File**: `src/bioetl/application/core/batch_executor_loop_progress.py`

### NAME-001: Class _BatchCheckpointRecoveryPort not PascalCase
- **File**: `src/bioetl/application/core/batch_executor_loop_progress.py`

### NAME-001: Class _BatchExecutorDQMixin not PascalCase
- **File**: `src/bioetl/application/core/batch_executor_dq_mixin.py`

### NAME-001: Class _EntityConstructor not PascalCase
- **File**: `src/bioetl/application/core/base_transformer_runtime.py`

### NAME-001: Class _IDMappingLifecycleState not PascalCase
- **File**: `src/bioetl/application/core/_idmapping_lifecycle_support.py`

### NAME-001: Class _BatchLoopStateProtocol not PascalCase
- **File**: `src/bioetl/application/core/batch_executor_loop_flow.py`

### NAME-001: Class _BatchStateUpdater not PascalCase
- **File**: `src/bioetl/application/core/batch_executor_loop_flow.py`

### NAME-001: Class _BatchFlushContextProtocol not PascalCase
- **File**: `src/bioetl/application/core/batch_executor_loop_flow.py`

### NAME-001: Class _BatchIterationContextProtocol not PascalCase
- **File**: `src/bioetl/application/core/batch_executor_loop_flow.py`

### NAME-001: Class _BatchStateUpdater not PascalCase
- **File**: `src/bioetl/application/core/batch_extraction_loop_service.py`

### NAME-001: Class _BatchProgressState not PascalCase
- **File**: `src/bioetl/application/core/batch_extraction_loop_service.py`

### NAME-001: Class _BatchStateUpdater not PascalCase
- **File**: `src/bioetl/application/core/batch_executor_loop_helpers.py`

### NAME-001: Class _FilteredFetchState not PascalCase
- **File**: `src/bioetl/application/core/_filtered_data_source_fetch_support.py`

### NAME-001: Class _HasPostrunRuntime not PascalCase
- **File**: `src/bioetl/application/core/postrun/_failure_policy.py`

### NAME-001: Class _HasPostrunFailureHandling not PascalCase
- **File**: `src/bioetl/application/core/postrun/_failure_policy.py`

### NAME-001: Class _BatchProgressInitializerPort not PascalCase
- **File**: `src/bioetl/application/core/batch_execution/lifecycle.py`

### NAME-001: Class _BatchCheckpointRecoveryLifecyclePort not PascalCase
- **File**: `src/bioetl/application/core/batch_execution/lifecycle.py`

### NAME-001: Class _BatchTracingLifecyclePort not PascalCase
- **File**: `src/bioetl/application/core/batch_execution/lifecycle.py`

### NAME-001: Class _BatchExtractionLoopRunner not PascalCase
- **File**: `src/bioetl/application/core/batch_execution/run_service.py`

### NAME-001: Class _DefaultContractPolicy not PascalCase
- **File**: `src/bioetl/application/core/base_transformer/contract_policy.py`

### NAME-001: Class _PreflightLoggingHostProtocol not PascalCase
- **File**: `src/bioetl/application/core/preflight/preflight_reporting.py`

### NAME-001: Class _CrossRefCoreBlock not PascalCase
- **File**: `src/bioetl/application/pipelines/common/blocks.py`

### NAME-001: Class _CrossRefJournalBlock not PascalCase
- **File**: `src/bioetl/application/pipelines/common/blocks.py`

### NAME-001: Class _CrossRefMetadataBlock not PascalCase
- **File**: `src/bioetl/application/pipelines/common/blocks.py`

### NAME-001: Class _CrossRefDateBlock not PascalCase
- **File**: `src/bioetl/application/pipelines/common/blocks.py`

### NAME-001: Class _CrossRefAuthorBlock not PascalCase
- **File**: `src/bioetl/application/pipelines/common/blocks.py`

### NAME-001: Class _PublicationDataExtractor not PascalCase
- **File**: `src/bioetl/application/pipelines/common/publication_assembly.py`

### NAME-001: Class _PublicationIdentifierResolver not PascalCase
- **File**: `src/bioetl/application/pipelines/common/publication_assembly.py`

### NAME-001: Class _PublicationMetadataStrategy not PascalCase
- **File**: `src/bioetl/application/pipelines/common/publication_assembly.py`

### NAME-001: Class _PublicationRecordNormalizer not PascalCase
- **File**: `src/bioetl/application/pipelines/common/publication_assembly.py`

### NAME-001: Class _ExtractionBlock not PascalCase
- **File**: `src/bioetl/application/pipelines/common/publication_blocks.py`

### NAME-001: Class _PubMedXmlBlock not PascalCase
- **File**: `src/bioetl/application/pipelines/pubmed/block_definitions.py`

### NAME-001: Class _PubMedIdentifierBlock not PascalCase
- **File**: `src/bioetl/application/pipelines/pubmed/block_definitions.py`

### NAME-001: Class _PubMedCoreBlock not PascalCase
- **File**: `src/bioetl/application/pipelines/pubmed/block_definitions.py`

### NAME-001: Class _PubMedAuthorBlock not PascalCase
- **File**: `src/bioetl/application/pipelines/pubmed/block_definitions.py`

### NAME-001: Class _PubMedJournalBlock not PascalCase
- **File**: `src/bioetl/application/pipelines/pubmed/block_definitions.py`

### NAME-001: Class _PubMedDateBlock not PascalCase
- **File**: `src/bioetl/application/pipelines/pubmed/block_definitions.py`

### NAME-001: Class _PubMedClassificationBlock not PascalCase
- **File**: `src/bioetl/application/pipelines/pubmed/block_definitions.py`

### NAME-001: Class _PubMedMetricsBlock not PascalCase
- **File**: `src/bioetl/application/pipelines/pubmed/block_definitions.py`

### NAME-001: Class _FeatureExtractorProtocol not PascalCase
- **File**: `src/bioetl/application/pipelines/uniprot/extractors/_feature_wrappers_mixin.py`

### NAME-001: Class _CompositeRunnerStageSupportHostProtocol not PascalCase
- **File**: `src/bioetl/application/composite/runner_pkg/runner_stage_support_types.py`

### NAME-001: Class _CompositeRunnerStageEnrichmentHostProtocol not PascalCase
- **File**: `src/bioetl/application/composite/runner_pkg/runner_stage_enrichment_types.py`

### NAME-001: Class _PreparedEnrichmentRunContext not PascalCase
- **File**: `src/bioetl/application/composite/runner_pkg/runner_stage_enrichment_types.py`

### NAME-001: Class _CheckpointManagerProtocol not PascalCase
- **File**: `src/bioetl/application/composite/runner_pkg/runner_runtime_helpers.py`

### NAME-001: Class _FSMRuntimeHelperProtocol not PascalCase
- **File**: `src/bioetl/application/composite/runner_pkg/runner_runtime_helpers.py`

### NAME-001: Class _CompositeRunnerHostProtocol not PascalCase
- **File**: `src/bioetl/application/composite/runner_pkg/runner_runtime_helpers.py`

### NAME-001: Class _CompositeLockedExecutionHostProtocol not PascalCase
- **File**: `src/bioetl/application/composite/runner_pkg/runner_execution_orchestrator.py`

### NAME-001: Class _CompositePreMergeExecutionResult not PascalCase
- **File**: `src/bioetl/application/composite/runner_pkg/runner_execution_orchestrator.py`

### NAME-001: Class _CompositeRunnerStageHostProtocol not PascalCase
- **File**: `src/bioetl/application/composite/runner_pkg/runner_stage_types.py`

### NAME-001: Class _PreparedDependenciesRunContext not PascalCase
- **File**: `src/bioetl/application/composite/runner_pkg/runner_stage_types.py`

### NAME-001: Class _DependencyPhaseOutcome not PascalCase
- **File**: `src/bioetl/application/composite/runner_pkg/runner_stage_types.py`

### NAME-001: Class _CompositeRunnerSupportHostProtocol not PascalCase
- **File**: `src/bioetl/application/composite/runner_pkg/runner_support_types.py`

### NAME-001: Class _PreparedPreflightValidationContext not PascalCase
- **File**: `src/bioetl/application/composite/runner_pkg/runner_support_types.py`

### NAME-001: Class _PreparedCompositeResultContext not PascalCase
- **File**: `src/bioetl/application/composite/runner_pkg/runner_support_types.py`

### NAME-001: Class _CompositeRunnerStageEnrichmentMixin not PascalCase
- **File**: `src/bioetl/application/composite/runner_pkg/runner_stage_enrichment_mixin.py`

### NAME-001: Class _CompositeRunnerControlPlaneHostProtocol not PascalCase
- **File**: `src/bioetl/application/composite/runner_pkg/runner_control_plane_mixin.py`

### NAME-001: Class _CompositePipelineFinalizationHostProtocol not PascalCase
- **File**: `src/bioetl/application/composite/runner_pkg/runner_completion_helpers.py`

### NAME-001: Class _CompositeRunnerMergeStageHostProtocol not PascalCase
- **File**: `src/bioetl/application/composite/runner_pkg/runner_merge_stage_types.py`

### NAME-001: Class _PreparedMergeInputs not PascalCase
- **File**: `src/bioetl/application/composite/runner_pkg/runner_merge_stage_types.py`

### NAME-001: Class _PreparedMergeRequest not PascalCase
- **File**: `src/bioetl/application/composite/runner_pkg/runner_merge_stage_types.py`

### NAME-001: Class _CompositeRunnerObservabilityHostProtocol not PascalCase
- **File**: `src/bioetl/application/composite/runner_pkg/runner_observability_mixin.py`

### NAME-001: Class _CompositeRunnerStageSupportMixin not PascalCase
- **File**: `src/bioetl/application/composite/runner_pkg/runner_stage_support_mixin.py`

### NAME-001: Class _RouteRequestSupport not PascalCase
- **File**: `src/bioetl/interfaces/http/health_server_http_mixin.py`

### NAME-001: Class _HealthResponseSupport not PascalCase
- **File**: `src/bioetl/interfaces/http/health_server_routing_mixin.py`

### NAME-001: Class _HealthStateSupport not PascalCase
- **File**: `src/bioetl/interfaces/http/health_server_routing_mixin.py`

### NAME-001: Class _ExportCommandService not PascalCase
- **File**: `src/bioetl/interfaces/cli/commands/export_support.py`

### NAME-001: Class _QuarantineManager not PascalCase
- **File**: `src/bioetl/interfaces/cli/commands/domains/quarantine/support.py`

### NAME-001: Class _QuarantineService not PascalCase
- **File**: `src/bioetl/interfaces/cli/commands/domains/quarantine/support.py`

### NAME-001: Class _QuarantineCommandContext not PascalCase
- **File**: `src/bioetl/interfaces/cli/commands/domains/quarantine/support.py`

### NAME-001: Class _BatchRunAccumulator not PascalCase
- **File**: `src/bioetl/interfaces/cli/commands/domains/run_all/support.py`

### NAME-001: Class _GetPipelineRunnerServiceFn not PascalCase
- **File**: `src/bioetl/interfaces/cli/commands/domains/run_all/execution.py`

### NAME-001: Class _NormalizationActivityMixin not PascalCase
- **File**: `src/bioetl/domain/services/normalization_service.py`

### NAME-001: Class _NormalizationBatchMixin not PascalCase
- **File**: `src/bioetl/domain/services/normalization_service.py`

### NAME-001: Class _BoundedIntVO not PascalCase
- **File**: `src/bioetl/domain/value_objects/molecular_descriptors.py`

### NAME-001: Class _BoundedFloatVO not PascalCase
- **File**: `src/bioetl/domain/value_objects/molecular_descriptors.py`

### NAME-001: Class _StageCompletionUpdate not PascalCase
- **File**: `src/bioetl/domain/control_plane/run_ledger.py`

### NAME-001: Class _PipelineRunAttrs not PascalCase
- **File**: `src/bioetl/domain/aggregates/_pipeline_run_read_model_mixin.py`

### NAME-001: Class _PipelineRunReadModelMixin not PascalCase
- **File**: `src/bioetl/domain/aggregates/_pipeline_run_read_model_mixin.py`

### NAME-001: Class _BatchAttrs not PascalCase
- **File**: `src/bioetl/domain/aggregates/_batch_mixins.py`

### NAME-001: Class _BatchReadModelMixin not PascalCase
- **File**: `src/bioetl/domain/aggregates/_batch_mixins.py`

### NAME-001: Class _BatchMutationMixin not PascalCase
- **File**: `src/bioetl/domain/aggregates/_batch_mixins.py`

### NAME-001: Class _BatchLifecycleMixin not PascalCase
- **File**: `src/bioetl/domain/aggregates/_batch_mixins.py`

### NAME-001: Class _PipelineRunLifecycleMixin not PascalCase
- **File**: `src/bioetl/domain/aggregates/_pipeline_run_mixins.py`

### NAME-001: Class _ExecutionPhaseNamespace not PascalCase
- **File**: `src/bioetl/domain/types/execution_phase_transitions.py`

### NAME-002: Function NOT_STARTED not snake_case
- **File**: `src/bioetl/domain/types/execution_phase_transitions.py`

### NAME-002: Function PREFLIGHT not snake_case
- **File**: `src/bioetl/domain/types/execution_phase_transitions.py`

### NAME-002: Function DEPENDENCY_EXECUTION not snake_case
- **File**: `src/bioetl/domain/types/execution_phase_transitions.py`

### NAME-002: Function ENRICHMENT not snake_case
- **File**: `src/bioetl/domain/types/execution_phase_transitions.py`

### NAME-002: Function MERGE not snake_case
- **File**: `src/bioetl/domain/types/execution_phase_transitions.py`

### NAME-002: Function CROSS_VALIDATION not snake_case
- **File**: `src/bioetl/domain/types/execution_phase_transitions.py`

### NAME-002: Function WRITE_FINALIZE not snake_case
- **File**: `src/bioetl/domain/types/execution_phase_transitions.py`

### NAME-002: Function COMPLETED_SUCCESS not snake_case
- **File**: `src/bioetl/domain/types/execution_phase_transitions.py`

### NAME-002: Function COMPLETED_WITH_WARNINGS not snake_case
- **File**: `src/bioetl/domain/types/execution_phase_transitions.py`

### NAME-002: Function FAILED_VALIDATION not snake_case
- **File**: `src/bioetl/domain/types/execution_phase_transitions.py`

### NAME-002: Function FAILED_EXECUTION not snake_case
- **File**: `src/bioetl/domain/types/execution_phase_transitions.py`

### NAME-002: Function FAILED_RECOVERY not snake_case
- **File**: `src/bioetl/domain/types/execution_phase_transitions.py`

### NAME-002: Function TERMINATED not snake_case
- **File**: `src/bioetl/domain/types/execution_phase_transitions.py`

### NAME-001: Class _PhaseTransitionNamespace not PascalCase
- **File**: `src/bioetl/domain/types/execution_phase_transitions.py`

### NAME-002: Function START_PREFLIGHT not snake_case
- **File**: `src/bioetl/domain/types/execution_phase_transitions.py`

### NAME-002: Function PREFLIGHT_TO_DEPENDENCIES not snake_case
- **File**: `src/bioetl/domain/types/execution_phase_transitions.py`

### NAME-002: Function DEPENDENCIES_TO_ENRICHMENT not snake_case
- **File**: `src/bioetl/domain/types/execution_phase_transitions.py`

### NAME-002: Function ENRICHMENT_TO_MERGE not snake_case
- **File**: `src/bioetl/domain/types/execution_phase_transitions.py`

### NAME-002: Function MERGE_TO_CROSS_VALIDATION not snake_case
- **File**: `src/bioetl/domain/types/execution_phase_transitions.py`

### NAME-002: Function CROSS_VALIDATION_TO_WRITE not snake_case
- **File**: `src/bioetl/domain/types/execution_phase_transitions.py`

### NAME-002: Function WRITE_TO_SUCCESS not snake_case
- **File**: `src/bioetl/domain/types/execution_phase_transitions.py`

### NAME-002: Function ANY_TO_FAILED not snake_case
- **File**: `src/bioetl/domain/types/execution_phase_transitions.py`

### NAME-001: Class _TransitionPolicyNamespace not PascalCase
- **File**: `src/bioetl/domain/types/execution_phase_transitions.py`

### NAME-002: Function ALLOW_RETRY not snake_case
- **File**: `src/bioetl/domain/types/execution_phase_transitions.py`

### NAME-002: Function CONTINUE_DEGRADED not snake_case
- **File**: `src/bioetl/domain/types/execution_phase_transitions.py`

### NAME-002: Function BLOCK_CONTINUATION not snake_case
- **File**: `src/bioetl/domain/types/execution_phase_transitions.py`

### NAME-001: Class _PhaseTransitionRuleBuilder not PascalCase
- **File**: `src/bioetl/domain/types/execution_phase_transitions.py`

### NAME-002: Function DeltaWriteConflictError not snake_case
- **File**: `src/bioetl/domain/exceptions/infrastructure/_delta.py`

### NAME-002: Function DeltaSchemaValidationError not snake_case
- **File**: `src/bioetl/domain/exceptions/infrastructure/_delta.py`

### NAME-002: Function DeltaOptimizeError not snake_case
- **File**: `src/bioetl/domain/exceptions/infrastructure/_delta.py`

### NAME-002: Function BucketNotFoundError not snake_case
- **File**: `src/bioetl/domain/exceptions/infrastructure/_storage.py`

### NAME-002: Function UploadError not snake_case
- **File**: `src/bioetl/domain/exceptions/infrastructure/_storage.py`

### NAME-002: Function BronzeValidationError not snake_case
- **File**: `src/bioetl/domain/exceptions/infrastructure/_storage.py`

### NAME-002: Function CachedBronzeEmptyError not snake_case
- **File**: `src/bioetl/domain/exceptions/infrastructure/_storage.py`

### NAME-002: Function DataValidationError not snake_case
- **File**: `src/bioetl/domain/exceptions/network/service.py`

### NAME-001: Class _NoOpSpan not PascalCase
- **File**: `src/bioetl/domain/ports/noop/_tracing.py`

### NAME-001: Class _NoOpOtelTracer not PascalCase
- **File**: `src/bioetl/domain/ports/noop/_tracing.py`

### NAME-001: Class _AggregatorHost not PascalCase
- **File**: `src/bioetl/domain/services/activity_aggregator/_aggregator_extensions.py`

### NAME-001: Class _ActivityAggregatorExtensions not PascalCase
- **File**: `src/bioetl/domain/services/activity_aggregator/_aggregator_extensions.py`

### NAME-001: Class _HealthCheckProbeOutcome not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/_health_check_policy.py`

### NAME-001: Class _SchemaBuilder not PascalCase
- **File**: `src/bioetl/infrastructure/config/contract_policy_validation.py`

### NAME-001: Class _ResolvedSchema not PascalCase
- **File**: `src/bioetl/infrastructure/config/contract_policy_validation.py`

### NAME-001: Class _ArrowSchemaLike not PascalCase
- **File**: `src/bioetl/infrastructure/config/contract_policy_validation.py`

### NAME-001: Class _CompositeSchema not PascalCase
- **File**: `src/bioetl/infrastructure/config/composite_config_api.py`

### NAME-001: Class _SpanProtocol not PascalCase
- **File**: `src/bioetl/infrastructure/observability/tracing.py`

### NAME-001: Class _SpanContextManagerProtocol not PascalCase
- **File**: `src/bioetl/infrastructure/observability/tracing.py`

### NAME-001: Class _TracerProtocol not PascalCase
- **File**: `src/bioetl/infrastructure/observability/tracing.py`

### NAME-001: Class _SpanHandle not PascalCase
- **File**: `src/bioetl/infrastructure/observability/tracing.py`

### NAME-001: Class _TracerAdapter not PascalCase
- **File**: `src/bioetl/infrastructure/observability/tracing.py`

### NAME-001: Class _SchemaBuilder not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold_writer.py`

### NAME-001: Class _ResolvedSchema not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold_writer.py`

### NAME-001: Class _BronzeMetadataWriteHostProtocol not PascalCase
- **File**: `src/bioetl/infrastructure/storage/bronze/metadata_operations.py`

### NAME-001: Class _BronzeWritePreparationHostProtocol not PascalCase
- **File**: `src/bioetl/infrastructure/storage/bronze/pipeline_helpers.py`

### NAME-001: Class _BronzeWriterSideEffectsHost not PascalCase
- **File**: `src/bioetl/infrastructure/storage/bronze/side_effects_mixin.py`

### NAME-001: Class _BronzeWriterMetricsHost not PascalCase
- **File**: `src/bioetl/infrastructure/storage/bronze/metrics_mixin.py`

### NAME-001: Class _PreparedMetadataWrite not PascalCase
- **File**: `src/bioetl/infrastructure/storage/metadata/writer_operations.py`

### NAME-001: Class _MetadataWriteRequest not PascalCase
- **File**: `src/bioetl/infrastructure/storage/metadata/writer_operations.py`

### NAME-001: Class _ResolvedMetadataTarget not PascalCase
- **File**: `src/bioetl/infrastructure/storage/metadata/writer_operations.py`

### NAME-001: Class _MetadataWriteTelemetryContext not PascalCase
- **File**: `src/bioetl/infrastructure/storage/metadata/writer_operations.py`

### NAME-001: Class _PreparedMetadataWriteOperation not PascalCase
- **File**: `src/bioetl/infrastructure/storage/metadata/writer_operations.py`

### NAME-001: Class _MetadataWriteRetryState not PascalCase
- **File**: `src/bioetl/infrastructure/storage/metadata/writer_operations.py`

### NAME-001: Class _MetadataWriteFinalTelemetry not PascalCase
- **File**: `src/bioetl/infrastructure/storage/metadata/writer_operations.py`

### NAME-001: Class _MetadataBuilderBase not PascalCase
- **File**: `src/bioetl/infrastructure/storage/metadata/builder_base.py`

### NAME-001: Class _SimpleGoldWriteRequest not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold/io_delta_runtime.py`

### NAME-001: Class _PreparedSimpleGoldWrite not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold/io_delta_runtime.py`

### NAME-001: Class _PreparedScd2GoldWrite not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold/io_delta_runtime.py`

### NAME-001: Class _GoldWriterSimpleDeltaHostProtocol not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold/io_delta_runtime.py`

### NAME-001: Class _GoldWriteAsyncioProtocol not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold/io_delta_runtime.py`

### NAME-001: Class _GoldWriteRetryModuleProtocol not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold/io_delta_runtime.py`

### NAME-001: Class _GoldWriterDeltaModuleProtocol not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold/io_delta_runtime.py`

### NAME-001: Class _GoldWriterScd2HostProtocol not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold/io_delta_runtime.py`

### NAME-001: Class _GoldMetadataWriteRequest not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold/metadata_operations.py`

### NAME-001: Class _GoldMergedMetadataWriteRequest not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold/metadata_operations.py`

### NAME-001: Class _PreparedGoldMetadataWrite not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold/metadata_operations.py`

### NAME-001: Class _GoldMetadataWriteHostProtocol not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold/metadata_operations.py`

### NAME-001: Class _GoldMergedMetadataWriteHostProtocol not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold/metadata_operations.py`

### NAME-001: Class _RunInExecutorHost not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold/validation_mixin.py`

### NAME-001: Class _GoldWritePreparationHostProtocol not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold/pipeline_helpers.py`

### NAME-001: Class _GoldWritePostwriteHostProtocol not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold/pipeline_helpers.py`

### NAME-001: Class _GoldMergedMetadataWriterProtocol not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold/io_mixin.py`

### NAME-001: Class _GoldWriteDispatchTargetProtocol not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold/io_mixin.py`

### NAME-001: Class _GoldMergedWriteHostProtocol not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold/io_mixin.py`

### NAME-001: Class _GoldMergedWriteRequest not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold/io_mixin.py`

### NAME-001: Class _PreparedGoldMergedWrite not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold/io_mixin.py`

### NAME-001: Class _GoldWriterMergedDispatchMixin not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold/io_mixin.py`

### NAME-001: Class _GoldAuditWriteRequest not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold/metadata_audit.py`

### NAME-001: Class _GoldMetadataAuditHostProtocol not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold/metadata_audit.py`

### NAME-001: Class _GoldWriterExecutorArrowMixin not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold/io_delta_mixins.py`

### NAME-001: Class _GoldWriterSimpleDeltaMixin not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold/io_delta_mixins.py`

### NAME-001: Class _GoldWriterScd2MergeMixin not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold/io_delta_mixins.py`

### NAME-001: Class _GoldWriterSCDHostProtocol not PascalCase
- **File**: `src/bioetl/infrastructure/storage/gold/io_helpers.py`

### NAME-001: Class _SilverWritePostwriteContext not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/postwrite_mixin.py`

### NAME-001: Class _SilverWriterPostwriteSelf not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/postwrite_mixin.py`

### NAME-001: Class _SilverAuditWriteRequest not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/audit_operations.py`

### NAME-001: Class _SilverAuditHostProtocol not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/audit_operations.py`

### NAME-001: Class _SilverWriterArrowContext not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/arrow_mixin.py`

### NAME-001: Class _SilverMetadataWriteRequest not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/metadata_operations.py`

### NAME-001: Class _SilverMergedMetadataWriteRequest not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/metadata_operations.py`

### NAME-001: Class _PreparedSilverMetadataWriteOperation not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/metadata_operations.py`

### NAME-001: Class _ResolvedSilverMetadataContext not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/metadata_operations.py`

### NAME-001: Class _PreparedSilverWriteFinalizationContext not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/metadata_operations.py`

### NAME-001: Class _SilverMetadataWriteHostProtocol not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/metadata_operations.py`

### NAME-001: Class _SilverWriteFinalizationHostProtocol not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/metadata_operations.py`

### NAME-001: Class _SilverWriteExecutionContext not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/pipeline_helpers.py`

### NAME-001: Class _SilverWriteInvocation not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/pipeline_helpers.py`

### NAME-001: Class _PreparedSilverWriteDispatcher not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/pipeline_helpers.py`

### NAME-001: Class _PreparedSilverWritePayloadBuilder not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/pipeline_helpers.py`

### NAME-001: Class _SilverWritePipelineCompleter not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/pipeline_helpers.py`

### NAME-001: Class _SilverWritePipelineExecutor not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/pipeline_helpers.py`

### NAME-001: Class _SilverSchemaDriftDiff not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/schema_drift_operations.py`

### NAME-001: Class _SchemaDriftHostProtocol not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/schema_drift_operations.py`

### NAME-001: Class _PreparedSilverWritePayload not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/validation_operations.py`

### NAME-001: Class _ValidatedSilverWriteContext not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/validation_operations.py`

### NAME-001: Class _SilverSchemaPolicyRequest not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/validation_operations.py`

### NAME-001: Class _SilverWritePreparationRequest not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/validation_operations.py`

### NAME-001: Class _SilverWriterValidationHostProtocol not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/validation_operations.py`

### NAME-001: Class _MergedSilverWriteRequest not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/merged_operations.py`

### NAME-001: Class _PreparedMergedSilverWrite not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/merged_operations.py`

### NAME-001: Class _SilverWriterMergedHostProtocol not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/merged_operations.py`

### NAME-001: Class _MergedSilverMetadataWriterProtocol not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/merged_mixin.py`

### NAME-001: Class _MergeExecutionTimeoutError not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/delta_helpers.py`

### NAME-001: Class _DeltaWriteRequest not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/delta_helpers.py`

### NAME-001: Class _DeltaWriteDispatchPolicy not PascalCase
- **File**: `src/bioetl/infrastructure/storage/silver/delta_helpers.py`

### NAME-001: Class _FetchState not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/common/fetch_retry_policy.py`

### NAME-001: Class _PubMedFallbackPolicyMixin not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/pubmed/_client_fallback_policy.py`

### NAME-001: Class _OpenAlexHealthHost not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/openalex/health_adapter_mixin.py`

### NAME-001: Class _OpenAlexRequestHost not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/openalex/_filter_fetch_requests.py`

### NAME-001: Class _FilteredFetchRequest not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/openalex/_filter_fetch_requests.py`

### NAME-001: Class _FallbackFetchRequest not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/openalex/_filter_fetch_requests.py`

### NAME-001: Class _FetchRequest not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/openalex/_filter_fetch_requests.py`

### NAME-001: Class _OpenAlexFilterFetchHost not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/openalex/_filter_fetch_flow.py`

### NAME-001: Class _SemanticScholarSearchFetchMixin not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/semanticscholar/_search_fetch_flow.py`

### NAME-001: Class _SupportsNormalizeDoi not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/semanticscholar/_client_fallback_policy.py`

### NAME-001: Class _SemanticScholarFallbackPolicyMixin not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/semanticscholar/_client_fallback_policy.py`

### NAME-001: Class _ChemblFallbackHost not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/chembl/_fetch_resilience_fallback.py`

### NAME-001: Class _ChemblFetchPagingFilteredMixin not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/chembl/_fetch_paging_filtered.py`

### NAME-001: Class _ChemblRecoveryHost not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/chembl/_fetch_resilience_recovery.py`

### NAME-001: Class _CanRetryCheck not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/http/_client_retry_flow.py`

### NAME-001: Class _RetryableErrorCheck not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/http/_client_retry_flow.py`

### NAME-001: Class _RetryDelayHandler not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/http/_client_retry_flow.py`

### NAME-001: Class _RetryLogger not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/http/_client_retry_flow.py`

### NAME-001: Class _RetryBudgetRecorder not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/http/_client_retry_flow.py`

### NAME-001: Class _StatusCodeResolver not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/http/_client_retry_flow.py`

### NAME-001: Class _ProviderHealthStateLike not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/http/_health_monitor_support.py`

### NAME-001: Class _OtelTracerLike not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/http/client_retry_observability.py`

### NAME-001: Class _RequestAttemptOutcome not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/http/_client_retry_models.py`

### NAME-001: Class _RetryRequestState not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/http/_client_retry_models.py`

### NAME-001: Class _CrossRefFallbackPolicyMixin not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/crossref/_client_fallback_policy.py`

### NAME-001: Class _PubChemClientFetchMixin not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/pubchem/_client_fetch_surface.py`

### NAME-001: Class _RequestRecorder not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/pubchem/fetch_flow.py`

### NAME-001: Class _PubChemSearchFetchMixin not PascalCase
- **File**: `src/bioetl/infrastructure/adapters/pubchem/_fetch_strategy_search.py`
