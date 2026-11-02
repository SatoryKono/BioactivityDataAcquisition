# Port Map Use Case -> Port -> Implementation (APP-002)

**Revision SHA:** acc8d0f344a048f8d659671f59da2de279a20616
**Method:** Static AST analysis for explicit `Port` interface declarations
**Wiring correction:** checked against composition factories at `acc8d0f344a048f8d659671f59da2de279a20616`. `CheckpointPort` resolves to `LocalCheckpointAdapter` via `create_checkpoint()`, `QuarantinePort` resolves to `UnifiedQuarantineAdapter` via `create_quarantine()`, and `BronzeStoragePort` / `MergedStoragePort` resolve to `StorageBundle` via `bootstrap_storage_adapter()`. Names with no class in the tree stay `NOT_VERIFIABLE`.

## 1. Unresolved / Dynamic Edges

- `AuditInspectionService` -> `AuditPort` -> `NOT_VERIFIABLE`
- `BaseServicesFactoryProtocol` -> `DataSourcePort` -> `NOT_VERIFIABLE`
- `BatchProcessingService` -> `BatchIdGeneratorPort` -> `NOT_VERIFIABLE`
- `CompositeCheckpointServiceContext` -> `CompositeCheckpointPort` -> `NOT_VERIFIABLE`
- `CompositeRunReportService` -> `RunReportStorePort` -> `NOT_VERIFIABLE`
- `ConfigService` -> `DomainConfigMapperPort` -> `NOT_VERIFIABLE`
- `ConfigService` -> `PipelineConfigLoaderPort` -> `NOT_VERIFIABLE`
- `ConfigService` -> `RegistryAccessorPort` -> `NOT_VERIFIABLE`
- `ConfigService` -> `SettingsLoaderPort` -> `NOT_VERIFIABLE`
- `DependencyResultService` -> `ExecutionMetricsReadablePort` -> `NOT_VERIFIABLE`
- `EnrichmentCoordinatorResultMixin` -> `ExecutionMetricsReadablePort` -> `NOT_VERIFIABLE`
- `HealthService` -> `ClockPort` -> `NOT_VERIFIABLE`
- `HealthService` -> `DataSourceFactoryPort` -> `NOT_VERIFIABLE`
- `HealthService` -> `HealthCheckPort` -> `NOT_VERIFIABLE`
- `MetricsService` -> `ClockPort` -> `NOT_VERIFIABLE`
- `MetricsService` -> `MetricsServerPort` -> `NOT_VERIFIABLE`
- `PipelineDataSourceServicesProtocol` -> `DataSourcePort` -> `NOT_VERIFIABLE`
- `PipelineDebugService` -> `PipelineDebugPort` -> `NOT_VERIFIABLE`
- `PipelinePostrunServicesProtocol` -> `StorageMaintenancePort` -> `NOT_VERIFIABLE`
- `PipelineRegistryProtocol` -> `PipelineFactoryPort` -> `NOT_VERIFIABLE`
- `PipelineRunExecutionService` -> `ClockPort` -> `NOT_VERIFIABLE`
- `PipelineRunExecutionService` -> `ExecutionMetricsRunnerPort` -> `NOT_VERIFIABLE`
- `PipelineRunExecutionService` -> `MetricsExtractorPort` -> `NOT_VERIFIABLE`
- `PipelineRunLifecycleService` -> `ClockPort` -> `NOT_VERIFIABLE`
- `PipelineRunnerService` -> `AuditPort` -> `NOT_VERIFIABLE`
- `PipelineRunnerService` -> `ClockPort` -> `NOT_VERIFIABLE`
- `PipelineRunnerService` -> `ExecutionMetricsRunnerPort` -> `NOT_VERIFIABLE`
- `PipelineRunnerService` -> `MetricsExtractorPort` -> `NOT_VERIFIABLE`
- `PipelineRunnerService` -> `RunReportStorePort` -> `NOT_VERIFIABLE`
- `PipelineRunnerService` -> `RunnerFactoryPort` -> `NOT_VERIFIABLE`
- `PipelineService` -> `DataSourcePort` -> `NOT_VERIFIABLE`
- `PipelineService` -> `TracingPort` -> `NOT_VERIFIABLE`
- `PostrunCompactService` -> `StorageMaintenancePort` -> `NOT_VERIFIABLE`
- `PostrunMetadataWriteService` -> `ExecutorMetricsPort` -> `NOT_VERIFIABLE`
- `PostrunMetadataWriteService` -> `StorageMaintenancePort` -> `NOT_VERIFIABLE`
- `PostrunService` -> `ExecutorMetricsPort` -> `NOT_VERIFIABLE`
- `PostrunServiceSupportMixin` -> `ExecutorMetricsPort` -> `NOT_VERIFIABLE`
- `PubMedPublicationTermEnrichmentService` -> `FilterableDataSourcePort` -> `NOT_VERIFIABLE`
- `PublicationTermExtractionHost` -> `DataSourcePort` -> `NOT_VERIFIABLE`
- `PublicationTermFilteringHost` -> `FilterableDataSourcePort` -> `NOT_VERIFIABLE`
- `StorageFactoryProtocol` -> `AuditPort` -> `NOT_VERIFIABLE`
- `VacuumService` -> `TableCollectorPort` -> `NOT_VERIFIABLE`
- `WorkflowRunnerService` -> `RunReportStorePort` -> `NOT_VERIFIABLE`
- `_CoordinatorExecutionHost` -> `ClockPort` -> `NOT_VERIFIABLE`
- `_CoordinatorExecutionHost` -> `ExecutionMetricsRunnerPort` -> `NOT_VERIFIABLE`
- `_DQReportGenerationHostProtocol` -> `BronzeDQConfigPort` -> `NOT_VERIFIABLE`
- `_DQReportGenerationHostProtocol` -> `GoldDQConfigPort` -> `NOT_VERIFIABLE`
- `_DQReportGenerationHostProtocol` -> `SilverDQConfigPort` -> `NOT_VERIFIABLE`
- `_DependencyCoordinatorExecutionHost` -> `ClockPort` -> `NOT_VERIFIABLE`
- `_GoldWriterHost` -> `GoldValidatorPort` -> `NOT_VERIFIABLE`
- `_MetricsStartHost` -> `ClockPort` -> `NOT_VERIFIABLE`
- `_MetricsStartHost` -> `MetricsServerPort` -> `NOT_VERIFIABLE`
- `_MetricsStatusHost` -> `MetricsServerPort` -> `NOT_VERIFIABLE`
- `_ObserverContextManagerMixin` -> `ClockPort` -> `NOT_VERIFIABLE`
- `_PipelineRunnerCleanupHostProtocol` -> `TracingPort` -> `NOT_VERIFIABLE`
- `_PostrunSupportHost` -> `ExecutorMetricsPort` -> `NOT_VERIFIABLE`

## 2. Discrepancies with Bindings Matrix (#12467)

The following bindings were resolved via verified production bindings (composition root) but may diverge from the strictly mapped matrix tests:

- `BaseServicesFactoryProtocol` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `BatchCheckpointRecoveryService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `BatchProcessingSupportService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `BatchProgressService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `BronzeCleanupService` -> `BronzeStoragePort`: Resolved to `StorageBundle` via production bindings, not matching base matrix explicitly.
- `BronzeCleanupService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `CheckpointCompatibilityService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `CheckpointRuntimeService` -> `CheckpointPort`: Resolved to `LocalCheckpointAdapter` via production bindings, not matching base matrix explicitly.
- `CheckpointRuntimeService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `CheckpointService` -> `CheckpointPort`: Resolved to `LocalCheckpointAdapter` via production bindings, not matching base matrix explicitly.
- `CheckpointService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `CheckpointValidationProtocol` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `CleanupService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `CoalescePolicyService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `ColumnOrderService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `CompositeCheckpointServiceContext` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `CompositeLifecycleObserverService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `CompositePreflightValidationService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `CompositeRunReportService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `CompositeRunnerObservabilityHostProtocol` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `ConfigDQService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `ConfigService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `ConflictResolverService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `ContractMigrationService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `ControlPlaneIntegrityMetricsService` -> `MetricsPort`: Resolved to `PrometheusMetrics` via production bindings, not matching base matrix explicitly.
- `ControlPlaneIntegrityMetricsService` -> `RunLedgerPort`: Resolved to `FileRunLedgerStore` via production bindings, not matching base matrix explicitly.
- `ControlPlaneIntegrityMetricsService` -> `RunManifestPort`: Resolved to `FileRunManifestStore` via production bindings, not matching base matrix explicitly.
- `DQReportService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `DQReportServiceFactoryProtocol` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `DataQualityMetricsHost` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `DataQualityService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `DataSourceCreatorProtocol` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `DependencyCoordinatorService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `DependencyJoinerService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `DependencyProgressService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `DependencyResultService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `EnricherDeduplicatorService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `EnrichmentCoordinatorResultMixin` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `EnrichmentCoordinatorService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `ErrorHandlerService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `ErrorHandlerService` -> `MetricsPort`: Resolved to `PrometheusMetrics` via production bindings, not matching base matrix explicitly.
- `ExportService` -> `DeltaReaderPort`: Resolved to `DeltaReader` via production bindings, not matching base matrix explicitly.
- `ExportService` -> `ExportCatalogPort`: Resolved to `ExportCatalogAdapter` via production bindings, not matching base matrix explicitly.
- `ExportService` -> `ExportWriterPort`: Resolved to `ExportWriterAdapter` via production bindings, not matching base matrix explicitly.
- `ExportService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `FSMStateHelperService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `ForensicRunDiffService` -> `RunManifestPort`: Resolved to `FileRunManifestStore` via production bindings, not matching base matrix explicitly.
- `HealthService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `HistoricalReplayCertificationService` -> `RunLedgerPort`: Resolved to `FileRunLedgerStore` via production bindings, not matching base matrix explicitly.
- `HistoricalReplayCertificationService` -> `RunManifestPort`: Resolved to `FileRunManifestStore` via production bindings, not matching base matrix explicitly.
- `HistoricalReplayCorpusService` -> `RunLedgerPort`: Resolved to `FileRunLedgerStore` via production bindings, not matching base matrix explicitly.
- `HistoricalReplayCorpusService` -> `RunManifestPort`: Resolved to `FileRunManifestStore` via production bindings, not matching base matrix explicitly.
- `JoinExecutorService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `JoinPlannerService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `KeyExtractorService` -> `DeltaReaderPort`: Resolved to `DeltaReader` via production bindings, not matching base matrix explicitly.
- `KeyExtractorService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `LifecycleTerminalEmitHost` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `LineageInspectionService` -> `LineageStorePort`: Resolved to `FileLineageStore` via production bindings, not matching base matrix explicitly.
- `LockRuntimeService` -> `LockPort`: Resolved to `MemoryLock` via production bindings, not matching base matrix explicitly.
- `LockRuntimeService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `LockRuntimeServiceCreateContext` -> `LockPort`: Resolved to `MemoryLock` via production bindings, not matching base matrix explicitly.
- `LockRuntimeServiceCreateContext` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `LockService` -> `LockPort`: Resolved to `MemoryLock` via production bindings, not matching base matrix explicitly.
- `LockService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `MedallionLifecycleService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `MergeService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `MergeService` -> `MergedStoragePort`: Resolved to `StorageBundle` via production bindings, not matching base matrix explicitly.
- `MetricsService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `PipelineDebugService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `PipelineRunExecutionService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `PipelineRunnerService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `PipelineRunnerService` -> `MetricsPort`: Resolved to `PrometheusMetrics` via production bindings, not matching base matrix explicitly.
- `PipelineRuntimeControlServicesProtocol` -> `CheckpointPort`: Resolved to `LocalCheckpointAdapter` via production bindings, not matching base matrix explicitly.
- `PipelineRuntimeControlServicesProtocol` -> `LockPort`: Resolved to `MemoryLock` via production bindings, not matching base matrix explicitly.
- `PipelineRuntimeControlServicesProtocol` -> `QuarantinePort`: Resolved to `UnifiedQuarantineAdapter` via production bindings, not matching base matrix explicitly.
- `PipelineService` -> `CheckpointPort`: Resolved to `LocalCheckpointAdapter` via production bindings, not matching base matrix explicitly.
- `PipelineService` -> `LockPort`: Resolved to `MemoryLock` via production bindings, not matching base matrix explicitly.
- `PipelineService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `PipelineService` -> `MetricsPort`: Resolved to `PrometheusMetrics` via production bindings, not matching base matrix explicitly.
- `PipelineService` -> `QuarantinePort`: Resolved to `UnifiedQuarantineAdapter` via production bindings, not matching base matrix explicitly.
- `PostrunCleanupService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `PostrunCompactService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `PostrunDQReportService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `PreflightSchemaFieldExtractionHost` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `PreflightService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `PreflightService` -> `MetricsPort`: Resolved to `PrometheusMetrics` via production bindings, not matching base matrix explicitly.
- `ProteinClassificationResolutionService` -> `ProteinClassificationPort`: Resolved to `ChEMBLProteinClassificationGraph` via production bindings, not matching base matrix explicitly.
- `ProviderDataSourceAccessProtocol` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `PubMedPublicationTermEnrichmentService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `QuarantineManagerSupportMixin` -> `QuarantinePort`: Resolved to `UnifiedQuarantineAdapter` via production bindings, not matching base matrix explicitly.
- `QuarantineRuntimeService` -> `QuarantinePort`: Resolved to `UnifiedQuarantineAdapter` via production bindings, not matching base matrix explicitly.
- `QuarantineService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `QuarantineService` -> `QuarantinePort`: Resolved to `UnifiedQuarantineAdapter` via production bindings, not matching base matrix explicitly.
- `ResolveProteinClassificationUseCase` -> `ProteinClassificationPort`: Resolved to `ChEMBLProteinClassificationGraph` via production bindings, not matching base matrix explicitly.
- `RunLedgerService` -> `RunLedgerPort`: Resolved to `FileRunLedgerStore` via production bindings, not matching base matrix explicitly.
- `RunManifestInspectionService` -> `RunManifestPort`: Resolved to `FileRunManifestStore` via production bindings, not matching base matrix explicitly.
- `RunManifestService` -> `RunManifestPort`: Resolved to `FileRunManifestStore` via production bindings, not matching base matrix explicitly.
- `ShutdownService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `StorageFactoryProtocol` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `StorageFactoryProtocol` -> `MetricsPort`: Resolved to `PrometheusMetrics` via production bindings, not matching base matrix explicitly.
- `SupportAwareDataSourceCreatorProtocol` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `VacuumService` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `WorkflowExecutionService` -> `LockPort`: Resolved to `MemoryLock` via production bindings, not matching base matrix explicitly.
- `WorkflowExecutionService` -> `WorkflowExecutionStatePort`: Resolved to `FileWorkflowExecutionStateStore` via production bindings, not matching base matrix explicitly.
- `WorkflowExecutionService` -> `WorkflowLedgerPort`: Resolved to `FileWorkflowLedgerStore` via production bindings, not matching base matrix explicitly.
- `WorkflowInspectionService` -> `WorkflowExecutionStatePort`: Resolved to `FileWorkflowExecutionStateStore` via production bindings, not matching base matrix explicitly.
- `WorkflowInspectionService` -> `WorkflowLedgerPort`: Resolved to `FileWorkflowLedgerStore` via production bindings, not matching base matrix explicitly.
- `WorkflowInspectionService` -> `WorkflowManifestPort`: Resolved to `FileWorkflowManifestStore` via production bindings, not matching base matrix explicitly.
- `WorkflowLedgerService` -> `WorkflowLedgerPort`: Resolved to `FileWorkflowLedgerStore` via production bindings, not matching base matrix explicitly.
- `WorkflowManifestService` -> `WorkflowManifestPort`: Resolved to `FileWorkflowManifestStore` via production bindings, not matching base matrix explicitly.
- `WorkflowRunnerService` -> `MetricsPort`: Resolved to `PrometheusMetrics` via production bindings, not matching base matrix explicitly.
- `WorkflowTransformService` -> `MetricsPort`: Resolved to `PrometheusMetrics` via production bindings, not matching base matrix explicitly.
- `_CompositeLifecycleTracingHost` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `_CompositePhaseStartHostProtocol` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `_CompositeRunnerMergeStageHostProtocol` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `_CompositeRunnerStageEnrichmentHostProtocol` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `_CompositeRunnerStageHostProtocol` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `_CompositeRunnerStageSupportHostProtocol` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `_CompositeRunnerSupportHostProtocol` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `_CoordinatorExecutionHost` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `_CoordinatorPlanningHost` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `_DQReportGenerationHostProtocol` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `_DependencyBatchHost` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `_DependencyCoordinatorExecutionHost` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `_FilteredQuarantineHost` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `_FilteredQuarantineHost` -> `QuarantinePort`: Resolved to `UnifiedQuarantineAdapter` via production bindings, not matching base matrix explicitly.
- `_LockRuntimeHostProtocol` -> `LockPort`: Resolved to `MemoryLock` via production bindings, not matching base matrix explicitly.- `_LockRuntimeHostProtocol` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `_MedallionLifecycleHostProtocol` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `_MergeIOHost` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `_MergeOutputHostProtocol` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `_MergeOutputHostProtocol` -> `MergedStoragePort`: Resolved to `StorageBundle` via production bindings, not matching base matrix explicitly.
- `_MetricsGatewayHost` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `_MetricsStartHost` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `_ObserverContextManagerMixin` -> `MetricsPort`: Resolved to `PrometheusMetrics` via production bindings, not matching base matrix explicitly.
- `_PipelineRunnerCleanupHostProtocol` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `_PipelineRunnerFlowHostProtocol` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `_PostrunHostAttrSurface` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `_PostrunHostAttrSurface` -> `MetricsPort`: Resolved to `PrometheusMetrics` via production bindings, not matching base matrix explicitly.
- `_QuarantineAsyncHost` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `_QuarantineAsyncHost` -> `QuarantinePort`: Resolved to `UnifiedQuarantineAdapter` via production bindings, not matching base matrix explicitly.
- `_QuarantineSyncHost` -> `LoggerPort`: Resolved to `UnifiedLogger` via production bindings, not matching base matrix explicitly.
- `_QuarantineSyncHost` -> `QuarantinePort`: Resolved to `UnifiedQuarantineAdapter` via production bindings, not matching base matrix explicitly.

## 3. Use Cases and their Ports

### `AuditInspectionService`
**Location:** `src/bioetl/application/services/export_lineage/audit_inspection_service.py`

| Port | Implementation | Status |
|---|---|---|
| `AuditPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `BaseServicesFactoryProtocol`
**Location:** `src/bioetl/application/ports/pipeline.py`

| Port | Implementation | Status |
|---|---|---|
| `DataSourcePort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `BatchCheckpointRecoveryService`
**Location:** `src/bioetl/application/core/batch_checkpoint_recovery_service.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `BatchMetricsRecorderService`
**Location:** `src/bioetl/application/core/batch_metrics.py`

| Port | Implementation | Status |
|---|---|---|
| `MetricsPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `BatchProcessingService`
**Location:** `src/bioetl/application/core/batch_processing_service.py`

| Port | Implementation | Status |
|---|---|---|
| `BatchIdGeneratorPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `BatchProcessingSupportService`
**Location:** `src/bioetl/application/core/batch_processing_support.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `BatchProgressService`
**Location:** `src/bioetl/application/core/batch_progress_service.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `BronzeCleanupService`
**Location:** `src/bioetl/application/services/ops/bronze_cleanup_service.py`

| Port | Implementation | Status |
|---|---|---|
| `BronzeStoragePort` | `StorageBundle` | RESOLVED |
| `ClockPort` | `SystemClock` | RESOLVED |
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
| `ClockPort` | `SystemClock` | RESOLVED |
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
| `GoldDQAnalyzerPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |
| `MetricsPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `DQReportWriterPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `SilverDQAnalyzerPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `DQReportServiceFactoryProtocol`
**Location:** `src/bioetl/application/ports/dq.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `DataQualityMetricsHost`
**Location:** `src/bioetl/application/services/quality/data_quality_anomalies.py`

| Port | Implementation | Status |
|---|---|---|
| `DQMonitorPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |
| `MetricsPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `DataQualityService`
**Location:** `src/bioetl/application/services/quality/data_quality_service.py`

| Port | Implementation | Status |
|---|---|---|
| `DQMonitorPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |
| `MetricsPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `DataSourceCreatorProtocol`
**Location:** `src/bioetl/application/ports/providers.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `DependencyCoordinatorService`
**Location:** `src/bioetl/application/composite/dependency_coordinator.py`

| Port | Implementation | Status |
|---|---|---|
| `ClockPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `DeltaReaderPort` | `DeltaReader` | RESOLVED |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `DependencyJoinerService`
**Location:** `src/bioetl/application/composite/dependency_joiner.py`

| Port | Implementation | Status |
|---|---|---|
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
| `ExecutionMetricsReadablePort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `EnricherDeduplicatorService`
**Location:** `src/bioetl/application/composite/deduplication.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `EnrichmentCoordinatorResultMixin`
**Location:** `src/bioetl/application/composite/coordinator_result_mixin.py`

| Port | Implementation | Status |
|---|---|---|
| `ExecutionMetricsReadablePort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `EnrichmentCoordinatorService`
**Location:** `src/bioetl/application/composite/coordinator.py`

| Port | Implementation | Status |
|---|---|---|
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
| `DeltaReaderPort` | `DeltaReader` | RESOLVED |
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
| `ClockPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `DataSourceFactoryPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `HealthCheckPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
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

### `JoinExecutorService`
**Location:** `src/bioetl/application/composite/join_execution.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `JoinPlannerService`
**Location:** `src/bioetl/application/composite/join_planner.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `KeyExtractorService`
**Location:** `src/bioetl/application/composite/key_extractor.py`

| Port | Implementation | Status |
|---|---|---|
| `DeltaReaderPort` | `DeltaReader` | RESOLVED |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `LifecycleTerminalEmitHost`
**Location:** `src/bioetl/application/composite/helpers/lifecycle_observer_terminal_emit.py`

| Port | Implementation | Status |
|---|---|---|
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
| `DeltaReaderPort` | `DeltaReader`; `CompositeReplayInputReader` (replay) | RESOLVED |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |
| `MergedStoragePort` | `StorageBundle` | RESOLVED |
| `SilverStoragePort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `MetricsService`
**Location:** `src/bioetl/application/services/ops/metrics_service.py`

| Port | Implementation | Status |
|---|---|---|
| `ClockPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |
| `MetricsServerPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `PipelineDataSourceServicesProtocol`
**Location:** `src/bioetl/application/core/pipeline_runtime_service_protocols.py`

| Port | Implementation | Status |
|---|---|---|
| `DataSourcePort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

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

### `PipelineRegistryProtocol`
**Location:** `src/bioetl/application/ports/pipeline_registry.py`

| Port | Implementation | Status |
|---|---|---|
| `PipelineFactoryPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `PipelineRunExecutionService`
**Location:** `src/bioetl/application/services/execution/pipeline_run_execution_service.py`

| Port | Implementation | Status |
|---|---|---|
| `ClockPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `ExecutionMetricsRunnerPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |
| `MetricsExtractorPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `PipelineRunLifecycleService`
**Location:** `src/bioetl/application/services/execution/pipeline_run_lifecycle_service.py`

| Port | Implementation | Status |
|---|---|---|
| `ClockPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `PipelineRunnerService`
**Location:** `src/bioetl/application/services/execution/pipeline_runner_service.py`

| Port | Implementation | Status |
|---|---|---|
| `AuditPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `ClockPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `ExecutionMetricsRunnerPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
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
| `DataSourcePort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `LockPort` | `MemoryLock` | RESOLVED |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |
| `MetricsPort` | `PrometheusMetrics` | RESOLVED |
| `QuarantinePort` | `UnifiedQuarantineAdapter` | RESOLVED |
| `TracingPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `PostrunCleanupService`
**Location:** `src/bioetl/application/core/postrun/cleanup_orchestrator.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `PostrunCompactService`
**Location:** `src/bioetl/application/core/postrun/compact_orchestrator.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |
| `StorageMaintenancePort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `PostrunDQReportService`
**Location:** `src/bioetl/application/core/postrun/dq_report_orchestrator.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `PostrunMetadataWriteService`
**Location:** `src/bioetl/application/core/postrun/metadata_write_service.py`

| Port | Implementation | Status |
|---|---|---|
| `ExecutorMetricsPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `StorageMaintenancePort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `PostrunService`
**Location:** `src/bioetl/application/core/postrun/service.py`

| Port | Implementation | Status |
|---|---|---|
| `ExecutorMetricsPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `TracingPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `PostrunServiceSupportMixin`
**Location:** `src/bioetl/application/core/postrun/_service_support.py`

| Port | Implementation | Status |
|---|---|---|
| `ExecutorMetricsPort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `PreflightSchemaFieldExtractionHost`
**Location:** `src/bioetl/application/composite/helpers/preflight_schema_field_extraction.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

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

### `ProviderDataSourceAccessProtocol`
**Location:** `src/bioetl/application/ports/providers.py`

| Port | Implementation | Status |
|---|---|---|
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `PubMedPublicationTermEnrichmentService`
**Location:** `src/bioetl/application/pipelines/pubmed/publication_term_enricher.py`

| Port | Implementation | Status |
|---|---|---|
| `FilterableDataSourcePort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |

### `PublicationTermExtractionHost`
**Location:** `src/bioetl/application/core/publication_term_extraction_mixin.py`

| Port | Implementation | Status |
|---|---|---|
| `DataSourcePort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `PublicationTermFilteringHost`
**Location:** `src/bioetl/application/core/publication_term_filtering_mixin.py`

| Port | Implementation | Status |
|---|---|---|
| `FilterableDataSourcePort` | `NOT_VERIFIABLE` | NOT_VERIFIABLE |

### `QuarantineManagerSupportMixin`
**Location:** `src/bioetl/application/core/_quarantine_manager_support.py`

| Port | Implementation | Status |
|---|---|---|
| `QuarantinePort` | `UnifiedQuarantineAdapter` | RESOLVED |

### `QuarantineRuntimeService`
**Location:** `src/bioetl/application/core/quarantine_manager.py`

| Port | Implementation | Status |
|---|---|---|
| `QuarantinePort` | `UnifiedQuarantineAdapter` | RESOLVED |

### `QuarantineService`
**Location:** `src/bioetl/application/services/quality/quarantine_service.py`

| Port | Implementation | Status |
|---|---|---|
| `ClockPort` | `SystemClock` | RESOLVED |
| `LoggerPort` | `UnifiedLogger` | RESOLVED |
| `QuarantinePort` | `UnifiedQuarantineAdapter` | RESOLVED |

### `QuarantineServiceSyncMixin`
**Location:** `src/bioetl/application/services/quality/_quarantine_service_sync_mixin.py`

| Port | Implementation | Status |
|---|---|---|
| `ClockPort` | `SystemClock` | RESOLVED |

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
