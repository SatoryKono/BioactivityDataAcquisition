# Port Map Use Case -> Port -> Implementation (APP-002)

**Revision SHA:** f07ead17df6283b9a7d2d8bfc7e10e2358f97c8b
**Method:** Static AST analysis for explicit `Port` interface declarations
**Wiring correction:** checked against composition factories at `f07ead17df6283b9a7d2d8bfc7e10e2358f97c8b`. `CheckpointPort` resolves to `LocalCheckpointAdapter` via `create_checkpoint()`, `QuarantinePort` resolves to `UnifiedQuarantineAdapter` via `create_quarantine()`, and `BronzeStoragePort` / `MergedStoragePort` resolve to `StorageBundle` via `bootstrap_storage_adapter()`. Names with no class in the tree stay `NOT_VERIFIABLE`.

## 1. Use Cases and their Ports

### `AuditInspectionService`
**Location:** `src/bioetl/application/services/export_lineage/audit_inspection_service.py`

| Port | Implementation | Status |
|---|---|---|
| `AuditPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `BatchMetricsRecorderService`
**Location:** `src/bioetl/application/core/batch_metrics.py`

| Port | Implementation | Status |
|---|---|---|
| `MetricsPort` | `PrometheusMetrics` | RESOLVED |

### `BatchTracingManagerService`
**Location:** `src/bioetl/application/core/batch_tracing.py`

| Port | Implementation | Status |
|---|---|---|
| `TracingPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `BronzeCleanupService`
**Location:** `src/bioetl/application/services/ops/bronze_cleanup_service.py`

| Port | Implementation | Status |
|---|---|---|
| `BronzeStoragePort` | `StorageBundle` | RESOLVED |
| `ClockPort` | `RuntimeClock` | RESOLVED |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `CheckpointCompatibilityService`
**Location:** `src/bioetl/application/services/checkpoint/checkpoint_compatibility_service.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `CheckpointRuntimeService`
**Location:** `src/bioetl/application/core/lifecycle/checkpoint_manager.py`

| Port | Implementation | Status |
|---|---|---|
| `CheckpointPort` | `LocalCheckpointAdapter` | RESOLVED |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `CheckpointService`
**Location:** `src/bioetl/application/services/checkpoint/checkpoint_service.py`

| Port | Implementation | Status |
|---|---|---|
| `CheckpointPort` | `LocalCheckpointAdapter` | RESOLVED |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `CheckpointValidationProtocol`
**Location:** `src/bioetl/application/core/lifecycle/checkpoint_load_validation.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `CleanupService`
**Location:** `src/bioetl/application/core/lifecycle/cleanup_service.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `CoalescePolicyService`
**Location:** `src/bioetl/application/composite/coalesce_policy.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `ColumnOrderService`
**Location:** `src/bioetl/application/composite/column_service.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `CompositeCheckpointServiceContext`
**Location:** `src/bioetl/application/composite/checkpoint/service.py`

| Port | Implementation | Status |
|---|---|---|
| `CompositeCheckpointPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `CompositeLifecycleObserverService`
**Location:** `src/bioetl/application/composite/lifecycle_observer_service.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `CompositePreflightValidationService`
**Location:** `src/bioetl/application/composite/preflight_validator.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `CompositeRunReportService`
**Location:** `src/bioetl/application/services/run_reports/composite.py`

| Port | Implementation | Status |
|---|---|---|
| `ClockPort` | `RuntimeClock` | RESOLVED |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |
| `RunReportStorePort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `CompositeRunnerObservabilityHostProtocol`
**Location:** `src/bioetl/application/composite/runner_pkg/runner_observability_helpers.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `ConfigDQService`
**Location:** `src/bioetl/application/services/quality/config_dq_service.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `ConfigService`
**Location:** `src/bioetl/application/services/ops/config_service.py`

| Port | Implementation | Status |
|---|---|---|
| `DomainConfigMapperPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |
| `PipelineConfigLoaderPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `RegistryAccessorPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `SettingsLoaderPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `ConflictResolverService`
**Location:** `src/bioetl/application/composite/conflict_resolver.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `ContractMigrationService`
**Location:** `src/bioetl/application/services/contracts/contract_migration_service.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `ControlPlaneIntegrityMetricsService`
**Location:** `src/bioetl/application/observability/control_plane_integrity_metrics.py`

| Port | Implementation | Status |
|---|---|---|
| `MetricsPort` | `PrometheusMetrics` | RESOLVED |
| `RunLedgerPort` | `FileRunLedgerStore` | RESOLVED |
| `RunManifestPort` | `FileRunManifestStore` | RESOLVED |

### `DQReportService`
**Location:** `src/bioetl/application/services/quality/dq_report_service.py`

| Port | Implementation | Status |
|---|---|---|
| `BronzeDQAnalyzerPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `DQReportWriterPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `GoldDQAnalyzerPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |
| `MetricsPort` | `PrometheusMetrics` | RESOLVED |
| `SilverDQAnalyzerPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `DataQualityService`
**Location:** `src/bioetl/application/services/quality/data_quality_service.py`

| Port | Implementation | Status |
|---|---|---|
| `DQMonitorPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |
| `MetricsPort` | `PrometheusMetrics` | RESOLVED |

### `DependencyCoordinatorService`
**Location:** `src/bioetl/application/composite/dependency_coordinator.py`

| Port | Implementation | Status |
|---|---|---|
| `ClockPort` | `RuntimeClock` | RESOLVED |
| `DeltaReaderPort` | `CompositeReplayInputReader` | RESOLVED |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `DependencyProgressService`
**Location:** `src/bioetl/application/composite/dependency_progress_tracker.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `DependencyResultService`
**Location:** `src/bioetl/application/composite/dependency_result_mapper.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `EnricherDeduplicatorService`
**Location:** `src/bioetl/application/composite/deduplication.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `EnrichmentCoordinatorService`
**Location:** `src/bioetl/application/composite/coordinator.py`

| Port | Implementation | Status |
|---|---|---|
| `ClockPort` | `RuntimeClock` | RESOLVED |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `ErrorHandlerService`
**Location:** `src/bioetl/application/services/ops/error_handler.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |
| `MetricsPort` | `PrometheusMetrics` | RESOLVED |

### `ExportService`
**Location:** `src/bioetl/application/services/export_lineage/export_service.py`

| Port | Implementation | Status |
|---|---|---|
| `DeltaReaderPort` | `CompositeReplayInputReader` | RESOLVED |
| `ExportCatalogPort` | `ExportCatalogAdapter` | RESOLVED |
| `ExportWriterPort` | `ExportWriterAdapter` | RESOLVED |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `FSMStateHelperService`
**Location:** `src/bioetl/application/composite/fsm_helper.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `ForensicRunDiffService`
**Location:** `src/bioetl/application/services/control_plane/forensic_diff_service.py`

| Port | Implementation | Status |
|---|---|---|
| `RunManifestPort` | `FileRunManifestStore` | RESOLVED |

### `HealthService`
**Location:** `src/bioetl/application/services/ops/health_service.py`

| Port | Implementation | Status |
|---|---|---|
| `ClockPort` | `RuntimeClock` | RESOLVED |
| `DataSourceFactoryPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `HistoricalReplayCertificationService`
**Location:** `src/bioetl/application/services/control_plane/replay/historical_certification_service.py`

| Port | Implementation | Status |
|---|---|---|
| `RunLedgerPort` | `FileRunLedgerStore` | RESOLVED |
| `RunManifestPort` | `FileRunManifestStore` | RESOLVED |

### `HistoricalReplayCorpusService`
**Location:** `src/bioetl/application/services/control_plane/replay/historical_corpus_service.py`

| Port | Implementation | Status |
|---|---|---|
| `RunLedgerPort` | `FileRunLedgerStore` | RESOLVED |
| `RunManifestPort` | `FileRunManifestStore` | RESOLVED |

### `JoinPlannerService`
**Location:** `src/bioetl/application/composite/join_planner.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `KeyExtractorService`
**Location:** `src/bioetl/application/composite/key_extractor.py`

| Port | Implementation | Status |
|---|---|---|
| `DeltaReaderPort` | `CompositeReplayInputReader` | RESOLVED |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `LineageInspectionService`
**Location:** `src/bioetl/application/services/lineage/lineage_inspection_service.py`

| Port | Implementation | Status |
|---|---|---|
| `LineageStorePort` | `FileLineageStore` | RESOLVED |

### `LockRuntimeService`
**Location:** `src/bioetl/application/core/lifecycle/lock_runtime_service.py`

| Port | Implementation | Status |
|---|---|---|
| `LockPort` | `MemoryLock` | RESOLVED |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `LockRuntimeServiceCreateContext`
**Location:** `src/bioetl/application/core/lifecycle/lock_runtime_service.py`

| Port | Implementation | Status |
|---|---|---|
| `LockPort` | `MemoryLock` | RESOLVED |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `LockService`
**Location:** `src/bioetl/application/services/ops/lock_service.py`

| Port | Implementation | Status |
|---|---|---|
| `LockPort` | `MemoryLock` | RESOLVED |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `MedallionLifecycleService`
**Location:** `src/bioetl/application/services/medallion/medallion_lifecycle.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `MergeService`
**Location:** `src/bioetl/application/composite/merge_service.py`

| Port | Implementation | Status |
|---|---|---|
| `DeltaReaderPort` | `CompositeReplayInputReader` | RESOLVED |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |
| `MergedStoragePort` | `StorageBundle` | RESOLVED |
| `SilverStoragePort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `MetricsService`
**Location:** `src/bioetl/application/services/ops/metrics_service.py`

| Port | Implementation | Status |
|---|---|---|
| `ClockPort` | `RuntimeClock` | RESOLVED |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |
| `MetricsServerPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `PipelineDataSourceServicesProtocol`
**Location:** `src/bioetl/application/core/pipeline_runtime_service_protocols.py`

| Port | Implementation | Status |
|---|---|---|
| `DataSourcePort` | `BaseHttpAdapter` | RESOLVED |

### `PipelineDebugService`
**Location:** `src/bioetl/application/services/export_lineage/pipeline_debug_service.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |
| `PipelineDebugPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `PipelinePostrunServicesProtocol`
**Location:** `src/bioetl/application/core/pipeline_aux_service_protocols.py`

| Port | Implementation | Status |
|---|---|---|
| `StorageMaintenancePort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `PipelineRunExecutionService`
**Location:** `src/bioetl/application/services/execution/pipeline_run_execution_service.py`

| Port | Implementation | Status |
|---|---|---|
| `ClockPort` | `RuntimeClock` | RESOLVED |

### `PipelineRunLifecycleService`
**Location:** `src/bioetl/application/services/execution/pipeline_run_lifecycle_service.py`

| Port | Implementation | Status |
|---|---|---|
| `ClockPort` | `RuntimeClock` | RESOLVED |

### `PipelineRunnerService`
**Location:** `src/bioetl/application/services/execution/pipeline_runner_service.py`

| Port | Implementation | Status |
|---|---|---|
| `AuditPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `ClockPort` | `RuntimeClock` | RESOLVED |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |
| `MetricsExtractorPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `MetricsPort` | `PrometheusMetrics` | RESOLVED |
| `RunReportStorePort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `RunnerFactoryPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `PipelineRuntimeControlServicesProtocol`
**Location:** `src/bioetl/application/core/pipeline_runtime_service_protocols.py`

| Port | Implementation | Status |
|---|---|---|
| `CheckpointPort` | `LocalCheckpointAdapter` | RESOLVED |
| `LockPort` | `MemoryLock` | RESOLVED |
| `QuarantinePort` | `UnifiedQuarantineAdapter` | RESOLVED |

### `PipelineService`
**Location:** `src/bioetl/application/core/pipeline_services.py`

| Port | Implementation | Status |
|---|---|---|
| `CheckpointPort` | `LocalCheckpointAdapter` | RESOLVED |
| `DataSourcePort` | `BaseHttpAdapter` | RESOLVED |
| `LockPort` | `MemoryLock` | RESOLVED |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |
| `MetricsPort` | `PrometheusMetrics` | RESOLVED |
| `QuarantinePort` | `UnifiedQuarantineAdapter` | RESOLVED |
| `TracingPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `PostrunService`
**Location:** `src/bioetl/application/core/postrun/service.py`

| Port | Implementation | Status |
|---|---|---|
| `TracingPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `PreflightService`
**Location:** `src/bioetl/application/core/preflight/service.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |
| `MetricsPort` | `PrometheusMetrics` | RESOLVED |

### `ProteinClassificationResolutionService`
**Location:** `src/bioetl/application/services/protein/classification_resolution.py`

| Port | Implementation | Status |
|---|---|---|
| `ProteinClassificationPort` | `ChEMBLProteinClassificationGraph` | RESOLVED |

### `PubMedPublicationTermEnrichmentService`
**Location:** `src/bioetl/application/pipelines/pubmed/publication_term_enricher.py`

| Port | Implementation | Status |
|---|---|---|
| `FilterableDataSourcePort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `QuarantineRuntimeService`
**Location:** `src/bioetl/application/core/quarantine_manager.py`

| Port | Implementation | Status |
|---|---|---|
| `MetricsPort` | `PrometheusMetrics` | RESOLVED |
| `QuarantinePort` | `UnifiedQuarantineAdapter` | RESOLVED |

### `QuarantineService`
**Location:** `src/bioetl/application/services/quality/quarantine_service.py`

| Port | Implementation | Status |
|---|---|---|
| `ClockPort` | `RuntimeClock` | RESOLVED |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |
| `QuarantinePort` | `UnifiedQuarantineAdapter` | RESOLVED |

### `QuarantineServiceSyncMixin`
**Location:** `src/bioetl/application/services/quality/_quarantine_service_sync_mixin.py`

| Port | Implementation | Status |
|---|---|---|
| `ClockPort` | `RuntimeClock` | RESOLVED |

### `ResolveProteinClassificationUseCase`
**Location:** `src/bioetl/application/services/protein/classification_resolution.py`

| Port | Implementation | Status |
|---|---|---|
| `ProteinClassificationPort` | `ChEMBLProteinClassificationGraph` | RESOLVED |

### `RunLedgerService`
**Location:** `src/bioetl/application/services/control_plane/ledger/service.py`

| Port | Implementation | Status |
|---|---|---|
| `RunLedgerPort` | `FileRunLedgerStore` | RESOLVED |

### `RunManifestInspectionService`
**Location:** `src/bioetl/application/services/control_plane/manifest/inspection_service.py`

| Port | Implementation | Status |
|---|---|---|
| `RunManifestPort` | `FileRunManifestStore` | RESOLVED |

### `RunManifestService`
**Location:** `src/bioetl/application/services/control_plane/manifest/service.py`

| Port | Implementation | Status |
|---|---|---|
| `RunManifestPort` | `FileRunManifestStore` | RESOLVED |

### `ShutdownService`
**Location:** `src/bioetl/application/services/ops/shutdown_service.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `VacuumService`
**Location:** `src/bioetl/application/services/ops/vacuum_service.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |
| `TableCollectorPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `WorkflowExecutionService`
**Location:** `src/bioetl/application/services/workflow/control_plane/execution_service.py`

| Port | Implementation | Status |
|---|---|---|
| `LockPort` | `MemoryLock` | RESOLVED |
| `WorkflowExecutionStatePort` | `FileWorkflowExecutionStateStore` | RESOLVED |
| `WorkflowLedgerPort` | `FileWorkflowLedgerStore` | RESOLVED |

### `WorkflowInspectionService`
**Location:** `src/bioetl/application/services/control_plane/workflow/inspection_service.py`

| Port | Implementation | Status |
|---|---|---|
| `WorkflowExecutionStatePort` | `FileWorkflowExecutionStateStore` | RESOLVED |
| `WorkflowLedgerPort` | `FileWorkflowLedgerStore` | RESOLVED |
| `WorkflowManifestPort` | `FileWorkflowManifestStore` | RESOLVED |

### `WorkflowLedgerService`
**Location:** `src/bioetl/application/services/control_plane/workflow/ledger_service.py`

| Port | Implementation | Status |
|---|---|---|
| `WorkflowLedgerPort` | `FileWorkflowLedgerStore` | RESOLVED |

### `WorkflowManifestService`
**Location:** `src/bioetl/application/services/control_plane/workflow/manifest_service.py`

| Port | Implementation | Status |
|---|---|---|
| `WorkflowManifestPort` | `FileWorkflowManifestStore` | RESOLVED |

### `WorkflowRunnerService`
**Location:** `src/bioetl/application/services/workflow/workflow_runner_service.py`

| Port | Implementation | Status |
|---|---|---|
| `MetricsPort` | `PrometheusMetrics` | RESOLVED |
| `RunReportStorePort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `WorkflowTransformService`
**Location:** `src/bioetl/application/services/workflow/workflow_transform_service.py`

| Port | Implementation | Status |
|---|---|---|
| `MetricsPort` | `PrometheusMetrics` | RESOLVED |

### `_CompositePhaseStartHostProtocol`
**Location:** `src/bioetl/application/composite/runner_pkg/runner_stage_start_flow.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `_CompositeRunnerMergeStageHostProtocol`
**Location:** `src/bioetl/application/composite/runner_pkg/runner_merge_stage_types.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `_CompositeRunnerStageEnrichmentHostProtocol`
**Location:** `src/bioetl/application/composite/runner_pkg/runner_stage_enrichment_types.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `_CompositeRunnerStageHostProtocol`
**Location:** `src/bioetl/application/composite/runner_pkg/runner_stage_types.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `_CompositeRunnerStageSupportHostProtocol`
**Location:** `src/bioetl/application/composite/runner_pkg/runner_stage_support_types.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `_CompositeRunnerSupportHostProtocol`
**Location:** `src/bioetl/application/composite/runner_pkg/runner_support_types.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `_DQReportGenerationHostProtocol`
**Location:** `src/bioetl/application/services/quality/dq_report_models.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `_LockRuntimeHostProtocol`
**Location:** `src/bioetl/application/core/lifecycle/lock_lifecycle.py`

| Port | Implementation | Status |
|---|---|---|
| `LockPort` | `MemoryLock` | RESOLVED |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `_MedallionLifecycleHostProtocol`
**Location:** `src/bioetl/application/services/medallion/medallion_lifecycle.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `_MergeOutputHostProtocol`
**Location:** `src/bioetl/application/composite/merger_output_mixin.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |
| `MergedStoragePort` | `StorageBundle` | RESOLVED |

### `_PipelineRunnerCleanupHostProtocol`
**Location:** `src/bioetl/application/core/_runner_support.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |
| `TracingPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `_PipelineRunnerFlowHostProtocol`
**Location:** `src/bioetl/application/core/runner_flow.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

## 2. Dependency Violations

No infrastructure/scripts imports detected in domain/application layers during static analysis.
All UseCases strictly depend on `*Port` interfaces. (MEASURED)
