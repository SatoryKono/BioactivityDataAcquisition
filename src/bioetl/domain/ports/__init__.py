"""Port interfaces (Protocols) for dependency inversion.

Implements RULES.md §1.1 - Ports & Adapters architecture.
This facade preserves historical ``from bioetl.domain.ports import X`` imports
without eagerly importing every port submodule during package initialization.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
<<<<<<< HEAD
from importlib import import_module
||||||| 20d05c514b

if TYPE_CHECKING:
    from bioetl.domain.ports.adr import (
        AdrDocument as AdrDocument,
    )
    from bioetl.domain.ports.adr import (
        AdrInfo as AdrInfo,
    )
    from bioetl.domain.ports.adr import (
        AdrServicePort as AdrServicePort,
    )
    from bioetl.domain.ports.adr import (
        AdrValidationIssue as AdrValidationIssue,
    )
    from bioetl.domain.ports.adr import (
        AdrValidationReport as AdrValidationReport,
    )
    from bioetl.domain.ports.audit import (
        AuditEntry as AuditEntry,
    )
    from bioetl.domain.ports.audit import (
        AuditLayer as AuditLayer,
    )
    from bioetl.domain.ports.audit import (
        AuditOperation as AuditOperation,
    )
    from bioetl.domain.ports.audit import (
        AuditPort as AuditPort,
    )
    from bioetl.domain.ports.config import (
        DomainConfigMapperPort as DomainConfigMapperPort,
    )
    from bioetl.domain.ports.config import (
        PipelineConfigLoaderPort as PipelineConfigLoaderPort,
    )
    from bioetl.domain.ports.config import (
        PipelineSettingsPort as PipelineSettingsPort,
    )
    from bioetl.domain.ports.config import (
        PipelineYamlConfigPort as PipelineYamlConfigPort,
    )
    from bioetl.domain.ports.config import (
        PublicationVocabularyPort as PublicationVocabularyPort,
    )
    from bioetl.domain.ports.config import (
        SettingsLoaderPort as SettingsLoaderPort,
    )
    from bioetl.domain.ports.config import (
        SettingsPort as SettingsPort,
    )
    from bioetl.domain.ports.control_plane import (
        ArtifactByteComparisonPort as ArtifactByteComparisonPort,
    )
    from bioetl.domain.ports.control_plane import (
        EffectiveConfigArtifactStorePort as EffectiveConfigArtifactStorePort,
    )
    from bioetl.domain.ports.control_plane import (
        LineageStorePort as LineageStorePort,
    )
    from bioetl.domain.ports.control_plane import (
        RunLedgerPort as RunLedgerPort,
    )
    from bioetl.domain.ports.control_plane import (
        RunManifestPort as RunManifestPort,
    )
    from bioetl.domain.ports.control_plane import (
        WorkflowExecutionStatePort as WorkflowExecutionStatePort,
    )
    from bioetl.domain.ports.control_plane import (
        WorkflowLedgerPort as WorkflowLedgerPort,
    )
    from bioetl.domain.ports.control_plane import (
        WorkflowManifestPort as WorkflowManifestPort,
    )
    from bioetl.domain.ports.data_normalization import (
        DataNormalizationPort as DataNormalizationPort,
    )
    from bioetl.domain.ports.data_source import (
        DataSourceFactoryPort as DataSourceFactoryPort,
    )
    from bioetl.domain.ports.data_source import (
        DataSourcePort as DataSourcePort,
    )
    from bioetl.domain.ports.data_source import (
        FilterableDataSourcePort as FilterableDataSourcePort,
    )
    from bioetl.domain.ports.delta_reader import DeltaReaderPort as DeltaReaderPort
    from bioetl.domain.ports.export import (
        ExportCatalogPort as ExportCatalogPort,
    )
    from bioetl.domain.ports.export import (
        ExportFileFingerprint as ExportFileFingerprint,
    )
    from bioetl.domain.ports.export import (
        ExportWriterPort as ExportWriterPort,
    )
    from bioetl.domain.ports.filtering import InputFilterPort as InputFilterPort
    from bioetl.domain.ports.health_check import (
        HealthCheckPort as HealthCheckPort,
    )
    from bioetl.domain.ports.health_check import (
        HealthCheckResult as HealthCheckResult,
    )
    from bioetl.domain.ports.health_check import (
        HealthMonitorPort as HealthMonitorPort,
    )
    from bioetl.domain.ports.health_check import (
        HealthStatePort as HealthStatePort,
    )
    from bioetl.domain.ports.health_check import (
        HealthStatusLiteral as HealthStatusLiteral,
    )
    from bioetl.domain.ports.idmapping import (
        IDMappingPort as IDMappingPort,
    )
    from bioetl.domain.ports.idmapping import (
        IDMappingSourceReaderPort as IDMappingSourceReaderPort,
    )
    from bioetl.domain.ports.metadata import (
        BronzeMetadataInput as BronzeMetadataInput,
    )
    from bioetl.domain.ports.metadata import (
        GoldMetadataInput as GoldMetadataInput,
    )
    from bioetl.domain.ports.metadata import (
        MetadataCoordinatorPort as MetadataCoordinatorPort,
    )
    from bioetl.domain.ports.metadata import (
        MetadataWriterPort as MetadataWriterPort,
    )
    from bioetl.domain.ports.metadata import (
        SilverMetadataInput as SilverMetadataInput,
    )
    from bioetl.domain.ports.metadata import (
        SilverRef as SilverRef,
    )
    from bioetl.domain.ports.observability import (
        DQMonitorPort as DQMonitorPort,
    )
    from bioetl.domain.ports.observability import (
        ExecutorMetricsPort as ExecutorMetricsPort,
    )
    from bioetl.domain.ports.observability import (
        LoggerPort as LoggerPort,
    )
    from bioetl.domain.ports.observability import (
        MetricLabels as MetricLabels,
    )
    from bioetl.domain.ports.observability import (
        MetricsPort as MetricsPort,
    )
    from bioetl.domain.ports.observability import (
        MetricsPublisherPort as MetricsPublisherPort,
    )
    from bioetl.domain.ports.observability import (
        MetricsServerPort as MetricsServerPort,
    )
    from bioetl.domain.ports.observability import (
        MetricsServerRuntimeStatus as MetricsServerRuntimeStatus,
    )
    from bioetl.domain.ports.observability import (
        TracingPort as TracingPort,
    )
    from bioetl.domain.ports.observability import (
        resolve_metric_labels as resolve_metric_labels,
    )
    from bioetl.domain.ports.pii import PiiHasherPort as PiiHasherPort
    from bioetl.domain.ports.protein_classification import (
        ProteinClassificationPort as ProteinClassificationPort,
    )
    from bioetl.domain.ports.publication_strategy import (
        DataExtractorStrategy as DataExtractorStrategy,
    )
    from bioetl.domain.ports.publication_strategy import (
        IdentifierResolverStrategy as IdentifierResolverStrategy,
    )
    from bioetl.domain.ports.publication_strategy import (
        PublicationMetadataStrategy as PublicationMetadataStrategy,
    )
    from bioetl.domain.ports.quality import (
        BronzeDQAnalyzerPort as BronzeDQAnalyzerPort,
    )
    from bioetl.domain.ports.quality import (
        BronzeDQConfigPort as BronzeDQConfigPort,
    )
    from bioetl.domain.ports.quality import (
        ContractPolicyProtocol as ContractPolicyProtocol,
    )
    from bioetl.domain.ports.quality import (
        DQReportWriterPort as DQReportWriterPort,
    )
    from bioetl.domain.ports.quality import (
        ErrorClassifierPort as ErrorClassifierPort,
    )
    from bioetl.domain.ports.quality import (
        ErrorHandlerPort as ErrorHandlerPort,
    )
    from bioetl.domain.ports.quality import (
        FallbackPolicyPort as FallbackPolicyPort,
    )
    from bioetl.domain.ports.quality import (
        GoldDQAnalyzerPort as GoldDQAnalyzerPort,
    )
    from bioetl.domain.ports.quality import (
        GoldDQConfigPort as GoldDQConfigPort,
    )
    from bioetl.domain.ports.quality import (
        GoldValidatorPort as GoldValidatorPort,
    )
    from bioetl.domain.ports.quality import (
        QuarantinePort as QuarantinePort,
    )
    from bioetl.domain.ports.quality import (
        QuarantineWriteRequest as QuarantineWriteRequest,
    )
    from bioetl.domain.ports.quality import (
        SilverDQAnalyzeRequest as SilverDQAnalyzeRequest,
    )
    from bioetl.domain.ports.quality import (
        SilverDQAnalyzerPort as SilverDQAnalyzerPort,
    )
    from bioetl.domain.ports.quality import (
        SilverDQConfigPort as SilverDQConfigPort,
    )
    from bioetl.domain.ports.quality import (
        SilverValidatorPort as SilverValidatorPort,
    )
    from bioetl.domain.ports.quality import (
        coerce_silver_dq_analyze_request as coerce_silver_dq_analyze_request,
    )
    from bioetl.domain.ports.resilience import (
        CircuitBreakerPort as CircuitBreakerPort,
    )
    from bioetl.domain.ports.resilience import (
        RateLimiterPort as RateLimiterPort,
    )
    from bioetl.domain.ports.runtime import (
        BatchIdGeneratorPort as BatchIdGeneratorPort,
    )
    from bioetl.domain.ports.runtime import (
        BreakpointHit as BreakpointHit,
    )
    from bioetl.domain.ports.runtime import (
        CheckpointPort as CheckpointPort,
    )
    from bioetl.domain.ports.runtime import (
        ClockPort as ClockPort,
    )
    from bioetl.domain.ports.runtime import (
        CompositeCheckpointPort as CompositeCheckpointPort,
    )
    from bioetl.domain.ports.runtime import (
        DebugAction as DebugAction,
    )
    from bioetl.domain.ports.runtime import (
        ExecutionMetricsReadablePort as ExecutionMetricsReadablePort,
    )
    from bioetl.domain.ports.runtime import (
        ExecutionMetricsRunnerPort as ExecutionMetricsRunnerPort,
    )
    from bioetl.domain.ports.runtime import (
        ExecutionObservabilityPort as ExecutionObservabilityPort,
    )
    from bioetl.domain.ports.runtime import (
        LockPort as LockPort,
    )
    from bioetl.domain.ports.runtime import (
        MemoryMonitorPort as MemoryMonitorPort,
    )
    from bioetl.domain.ports.runtime import (
        MemoryStats as MemoryStats,
    )
    from bioetl.domain.ports.runtime import (
        MetricsExtractorPort as MetricsExtractorPort,
    )
    from bioetl.domain.ports.runtime import (
        PipelineDebugPort as PipelineDebugPort,
    )
    from bioetl.domain.ports.runtime import (
        PipelineFactoryPort as PipelineFactoryPort,
    )
    from bioetl.domain.ports.runtime import (
        PipelineRegistryPort as PipelineRegistryPort,
    )
    from bioetl.domain.ports.runtime import (
        PipelineSnapshot as PipelineSnapshot,
    )
    from bioetl.domain.ports.runtime import (
        RegistryAccessorPort as RegistryAccessorPort,
    )
    from bioetl.domain.ports.runtime import (
        RunnablePort as RunnablePort,
    )
    from bioetl.domain.ports.runtime import (
        RunnerFactoryPort as RunnerFactoryPort,
    )
    from bioetl.domain.ports.runtime import (
        ShutdownPort as ShutdownPort,
    )
    from bioetl.domain.ports.runtime import (
        StageBreakpoint as StageBreakpoint,
    )
    from bioetl.domain.ports.runtime.memory import (
        MemoryDecisionTraceEntry as MemoryDecisionTraceEntry,
    )
    from bioetl.domain.ports.runtime.runner import (
        PipelineControlPlaneArtifacts as PipelineControlPlaneArtifacts,
    )
    from bioetl.domain.ports.runtime.runner import (
        PipelineCreateRunnerRequest as PipelineCreateRunnerRequest,
    )
    from bioetl.domain.ports.runtime.runner import (
        PipelineCreateWithServicesRequest as PipelineCreateWithServicesRequest,
    )
    from bioetl.domain.ports.serialization import JsonEncoderPort as JsonEncoderPort
    from bioetl.domain.ports.storage import (
        BronzeStoragePort as BronzeStoragePort,
    )
    from bioetl.domain.ports.storage import (
        GoldStoragePort as GoldStoragePort,
    )
    from bioetl.domain.ports.storage import (
        MergedStoragePort as MergedStoragePort,
    )
    from bioetl.domain.ports.storage import (
        SilverStoragePort as SilverStoragePort,
    )
    from bioetl.domain.ports.storage import (
        SilverWriteRequest as SilverWriteRequest,
    )
    from bioetl.domain.ports.storage import (
        StorageLifecyclePort as StorageLifecyclePort,
    )
    from bioetl.domain.ports.storage import (
        StorageMaintenancePort as StorageMaintenancePort,
    )
    from bioetl.domain.ports.storage import (
        coerce_silver_write_request as coerce_silver_write_request,
    )
    from bioetl.domain.ports.workflow_foreign_key_reconciliation import (
        ForeignKeyReconciliationPort as ForeignKeyReconciliationPort,
    )
    from bioetl.domain.ports.workflow_foreign_key_reconciliation import (
        ForeignKeyReconciliationRequest as ForeignKeyReconciliationRequest,
    )
    from bioetl.domain.ports.workflow_foreign_key_reconciliation import (
        ForeignKeyReconciliationResult as ForeignKeyReconciliationResult,
    )
    from bioetl.domain.ports.workflow_row_reconciliation import (
        RowReconciliationConfig as RowReconciliationConfig,
    )
    from bioetl.domain.ports.workflow_row_reconciliation import (
        RowReconciliationConfigError as RowReconciliationConfigError,
    )
    from bioetl.domain.ports.workflow_row_reconciliation import (
        RowReconciliationError as RowReconciliationError,
    )
    from bioetl.domain.ports.workflow_row_reconciliation import (
        RowReconciliationExecutionError as RowReconciliationExecutionError,
    )
    from bioetl.domain.ports.workflow_row_reconciliation import (
        RowReconciliationLayer as RowReconciliationLayer,
    )
    from bioetl.domain.ports.workflow_row_reconciliation import (
        RowReconciliationMissingColumnError as RowReconciliationMissingColumnError,
    )
    from bioetl.domain.ports.workflow_row_reconciliation import (
        RowReconciliationPort as RowReconciliationPort,
    )
    from bioetl.domain.ports.workflow_row_reconciliation import (
        RowReconciliationResult as RowReconciliationResult,
    )
    from bioetl.domain.ports.workflow_row_reconciliation import (
        RowReconciliationTypePolicy as RowReconciliationTypePolicy,
    )
    from bioetl.domain.ports.workflow_row_reconciliation import (
        RowReconciliationTypePolicyError as RowReconciliationTypePolicyError,
    )
=======

if TYPE_CHECKING:
    from bioetl.domain.ports.adr import (
        AdrDocument as AdrDocument,
        AdrInfo as AdrInfo,
        AdrServicePort as AdrServicePort,
        AdrValidationIssue as AdrValidationIssue,
        AdrValidationReport as AdrValidationReport,
    )
    from bioetl.domain.ports.audit import (
        AuditEntry as AuditEntry,
        AuditLayer as AuditLayer,
        AuditOperation as AuditOperation,
        AuditPort as AuditPort,
    )
    from bioetl.domain.ports.config import (
        DomainConfigMapperPort as DomainConfigMapperPort,
        PipelineConfigLoaderPort as PipelineConfigLoaderPort,
        PipelineSettingsPort as PipelineSettingsPort,
        PipelineYamlConfigPort as PipelineYamlConfigPort,
        PublicationVocabularyPort as PublicationVocabularyPort,
        SettingsLoaderPort as SettingsLoaderPort,
        SettingsPort as SettingsPort,
    )
    from bioetl.domain.ports.control_plane import (
        ArtifactByteComparisonPort as ArtifactByteComparisonPort,
        EffectiveConfigArtifactStorePort as EffectiveConfigArtifactStorePort,
        LineageStorePort as LineageStorePort,
        RunLedgerPort as RunLedgerPort,
        RunManifestPort as RunManifestPort,
        WorkflowExecutionStatePort as WorkflowExecutionStatePort,
        WorkflowLedgerPort as WorkflowLedgerPort,
        WorkflowManifestPort as WorkflowManifestPort,
    )
    from bioetl.domain.ports.data_normalization import (
        DataNormalizationPort as DataNormalizationPort,
    )
    from bioetl.domain.ports.data_source import (
        DataSourceFactoryPort as DataSourceFactoryPort,
        DataSourcePort as DataSourcePort,
        FilterableDataSourcePort as FilterableDataSourcePort,
    )
    from bioetl.domain.ports.delta_reader import DeltaReaderPort as DeltaReaderPort
    from bioetl.domain.ports.export import (
        ExportCatalogPort as ExportCatalogPort,
        ExportFileFingerprint as ExportFileFingerprint,
        ExportWriterPort as ExportWriterPort,
    )
    from bioetl.domain.ports.filtering import InputFilterPort as InputFilterPort
    from bioetl.domain.ports.health_check import (
        HealthCheckPort as HealthCheckPort,
        HealthCheckResult as HealthCheckResult,
        HealthMonitorPort as HealthMonitorPort,
        HealthStatePort as HealthStatePort,
        HealthStatusLiteral as HealthStatusLiteral,
    )
    from bioetl.domain.ports.idmapping import (
        IDMappingPort as IDMappingPort,
        IDMappingSourceReaderPort as IDMappingSourceReaderPort,
    )
    from bioetl.domain.ports.metadata import (
        BronzeMetadataInput as BronzeMetadataInput,
        GoldMetadataInput as GoldMetadataInput,
        MetadataCoordinatorPort as MetadataCoordinatorPort,
        MetadataWriterPort as MetadataWriterPort,
        SilverMetadataInput as SilverMetadataInput,
        SilverRef as SilverRef,
    )
    from bioetl.domain.ports.observability import (
        DQMonitorPort as DQMonitorPort,
        ExecutorMetricsPort as ExecutorMetricsPort,
        LoggerPort as LoggerPort,
        MetricLabels as MetricLabels,
        MetricsPort as MetricsPort,
        MetricsPublisherPort as MetricsPublisherPort,
        MetricsServerPort as MetricsServerPort,
        MetricsServerRuntimeStatus as MetricsServerRuntimeStatus,
        TracingPort as TracingPort,
        resolve_metric_labels as resolve_metric_labels,
    )
    from bioetl.domain.ports.pii import PiiHasherPort as PiiHasherPort
    from bioetl.domain.ports.protein_classification import (
        ProteinClassificationPort as ProteinClassificationPort,
    )
    from bioetl.domain.ports.publication_strategy import (
        DataExtractorStrategy as DataExtractorStrategy,
        IdentifierResolverStrategy as IdentifierResolverStrategy,
        PublicationMetadataStrategy as PublicationMetadataStrategy,
    )
    from bioetl.domain.ports.quality import (
        BronzeDQAnalyzerPort as BronzeDQAnalyzerPort,
        BronzeDQConfigPort as BronzeDQConfigPort,
        ContractPolicyProtocol as ContractPolicyProtocol,
        DQReportWriterPort as DQReportWriterPort,
        ErrorClassifierPort as ErrorClassifierPort,
        ErrorHandlerPort as ErrorHandlerPort,
        FallbackPolicyPort as FallbackPolicyPort,
        GoldDQAnalyzerPort as GoldDQAnalyzerPort,
        GoldDQConfigPort as GoldDQConfigPort,
        GoldValidatorPort as GoldValidatorPort,
        QuarantinePort as QuarantinePort,
        QuarantineWriteRequest as QuarantineWriteRequest,
        SilverDQAnalyzeRequest as SilverDQAnalyzeRequest,
        SilverDQAnalyzerPort as SilverDQAnalyzerPort,
        SilverDQConfigPort as SilverDQConfigPort,
        SilverValidatorPort as SilverValidatorPort,
        coerce_silver_dq_analyze_request as coerce_silver_dq_analyze_request,
    )
    from bioetl.domain.ports.resilience import (
        CircuitBreakerPort as CircuitBreakerPort,
        RateLimiterPort as RateLimiterPort,
    )
    from bioetl.domain.ports.runtime import (
        BatchIdGeneratorPort as BatchIdGeneratorPort,
        BreakpointHit as BreakpointHit,
        CheckpointPort as CheckpointPort,
        ClockPort as ClockPort,
        CompositeCheckpointPort as CompositeCheckpointPort,
        DebugAction as DebugAction,
        ExecutionMetricsReadablePort as ExecutionMetricsReadablePort,
        ExecutionMetricsRunnerPort as ExecutionMetricsRunnerPort,
        ExecutionObservabilityPort as ExecutionObservabilityPort,
        LockPort as LockPort,
        MemoryMonitorPort as MemoryMonitorPort,
        MemoryStats as MemoryStats,
        MetricsExtractorPort as MetricsExtractorPort,
        PipelineDebugPort as PipelineDebugPort,
        PipelineFactoryPort as PipelineFactoryPort,
        PipelineRegistryPort as PipelineRegistryPort,
        PipelineSnapshot as PipelineSnapshot,
        RegistryAccessorPort as RegistryAccessorPort,
        RunnablePort as RunnablePort,
        RunnerFactoryPort as RunnerFactoryPort,
        ShutdownPort as ShutdownPort,
        StageBreakpoint as StageBreakpoint,
    )
    from bioetl.domain.ports.runtime.memory import (
        MemoryDecisionTraceEntry as MemoryDecisionTraceEntry,
    )
    from bioetl.domain.ports.runtime.runner import (
        PipelineControlPlaneArtifacts as PipelineControlPlaneArtifacts,
        PipelineCreateRunnerRequest as PipelineCreateRunnerRequest,
        PipelineCreateWithServicesRequest as PipelineCreateWithServicesRequest,
    )
    from bioetl.domain.ports.serialization import JsonEncoderPort as JsonEncoderPort
    from bioetl.domain.ports.storage import (
        BronzeStoragePort as BronzeStoragePort,
        GoldStoragePort as GoldStoragePort,
        MergedStoragePort as MergedStoragePort,
        SilverStoragePort as SilverStoragePort,
        SilverWriteRequest as SilverWriteRequest,
        StorageLifecyclePort as StorageLifecyclePort,
        StorageMaintenancePort as StorageMaintenancePort,
        coerce_silver_write_request as coerce_silver_write_request,
    )
    from bioetl.domain.ports.workflow_foreign_key_reconciliation import (
        ForeignKeyReconciliationPort as ForeignKeyReconciliationPort,
        ForeignKeyReconciliationRequest as ForeignKeyReconciliationRequest,
        ForeignKeyReconciliationResult as ForeignKeyReconciliationResult,
    )
    from bioetl.domain.ports.workflow_row_reconciliation import (
        RowReconciliationConfig as RowReconciliationConfig,
        RowReconciliationConfigError as RowReconciliationConfigError,
        RowReconciliationError as RowReconciliationError,
        RowReconciliationExecutionError as RowReconciliationExecutionError,
        RowReconciliationLayer as RowReconciliationLayer,
        RowReconciliationMissingColumnError as RowReconciliationMissingColumnError,
        RowReconciliationPort as RowReconciliationPort,
        RowReconciliationResult as RowReconciliationResult,
        RowReconciliationTypePolicy as RowReconciliationTypePolicy,
        RowReconciliationTypePolicyError as RowReconciliationTypePolicyError,
    )
>>>>>>> master_20260719-2

_EXPORT_GROUPS: dict[str, tuple[str, ...]] = {
    "bioetl.domain.ports.adr": (
        "AdrDocument",
        "AdrInfo",
        "AdrServicePort",
        "AdrValidationIssue",
        "AdrValidationReport",
    ),
    "bioetl.domain.ports.audit": (
        "AuditEntry",
        "AuditLayer",
        "AuditOperation",
        "AuditPort",
    ),
    "bioetl.domain.ports.config": (
        "DomainConfigMapperPort",
        "PipelineConfigLoaderPort",
        "PipelineSettingsPort",
        "PipelineYamlConfigPort",
        "PublicationVocabularyPort",
        "SettingsLoaderPort",
        "SettingsPort",
    ),
    "bioetl.domain.ports.control_plane": (
        "ArtifactByteComparisonPort",
        "EffectiveConfigArtifactStorePort",
        "LineageStorePort",
        "RunLedgerPort",
        "RunManifestPort",
        "WorkflowExecutionStatePort",
        "WorkflowLedgerPort",
        "WorkflowManifestPort",
    ),
    "bioetl.domain.ports.data_normalization": ("DataNormalizationPort",),
    "bioetl.domain.ports.data_source": (
        "DataSourceFactoryPort",
        "DataSourcePort",
        "FilterableDataSourcePort",
    ),
    "bioetl.domain.ports.delta_reader": ("DeltaReaderPort",),
    "bioetl.domain.ports.export": (
        "ExportCatalogPort",
        "ExportFileFingerprint",
        "ExportWriterPort",
    ),
    "bioetl.domain.ports.filtering": ("InputFilterPort",),
    "bioetl.domain.ports.health_check": (
        "HealthCheckPort",
        "HealthCheckResult",
        "HealthMonitorPort",
        "HealthStatePort",
        "HealthStatusLiteral",
    ),
    "bioetl.domain.ports.idmapping": (
        "IDMappingPort",
        "IDMappingSourceReaderPort",
    ),
    "bioetl.domain.ports.metadata": (
        "BronzeMetadataInput",
        "GoldMetadataInput",
        "MetadataCoordinatorPort",
        "MetadataWriterPort",
        "SilverMetadataInput",
        "SilverRef",
    ),
    "bioetl.domain.ports.observability": (
        "DQMonitorPort",
        "ExecutorMetricsPort",
        "LoggerPort",
        "MetricLabels",
        "MetricsPort",
        "MetricsPublisherPort",
        "MetricsServerPort",
        "MetricsServerRuntimeStatus",
        "TracingPort",
        "resolve_metric_labels",
    ),
    "bioetl.domain.ports.pii": ("PiiHasherPort",),
    "bioetl.domain.ports.publication_strategy": (
        "DataExtractorStrategy",
        "IdentifierResolverStrategy",
        "PublicationMetadataStrategy",
    ),
    "bioetl.domain.ports.protein_classification": ("ProteinClassificationPort",),
    "bioetl.domain.ports.quality": (
        "BronzeDQAnalyzerPort",
        "BronzeDQConfigPort",
        "ContractPolicyProtocol",
        "DQReportWriterPort",
        "ErrorClassifierPort",
        "ErrorHandlerPort",
        "FallbackPolicyPort",
        "GoldDQAnalyzerPort",
        "GoldDQConfigPort",
        "GoldValidatorPort",
        "QuarantinePort",
        "QuarantineWriteRequest",
        "SilverDQAnalyzeRequest",
        "SilverDQAnalyzerPort",
        "SilverDQConfigPort",
        "SilverValidatorPort",
        "coerce_silver_dq_analyze_request",
    ),
    "bioetl.domain.ports.resilience": (
        "CircuitBreakerPort",
        "RateLimiterPort",
    ),
    "bioetl.domain.ports.runtime": (
        "BatchIdGeneratorPort",
        "BreakpointHit",
        "CheckpointPort",
        "ClockPort",
        "CompositeCheckpointPort",
        "DebugAction",
        "ExecutionMetricsReadablePort",
        "ExecutionMetricsRunnerPort",
        "ExecutionObservabilityPort",
        "LockPort",
        "MemoryMonitorPort",
        "MemoryStats",
        "MetricsExtractorPort",
        "PipelineDebugPort",
        "PipelineFactoryPort",
        "PipelineRegistryPort",
        "PipelineSnapshot",
        "RegistryAccessorPort",
        "RunnablePort",
        "RunnerFactoryPort",
        "ShutdownPort",
        "StageBreakpoint",
    ),
    "bioetl.domain.ports.runtime.memory": ("MemoryDecisionTraceEntry",),
    "bioetl.domain.ports.runtime.runner": (
        "PipelineControlPlaneArtifacts",
        "PipelineCreateRunnerRequest",
        "PipelineCreateWithServicesRequest",
    ),
    "bioetl.domain.ports.serialization": ("JsonEncoderPort",),
    "bioetl.domain.ports.storage": (
        "BronzeStoragePort",
        "GoldStoragePort",
        "MergedStoragePort",
        "SilverStoragePort",
        "SilverWriteRequest",
        "StorageLifecyclePort",
        "StorageMaintenancePort",
        "coerce_silver_write_request",
    ),
    "bioetl.domain.ports.workflow_foreign_key_reconciliation": (
        "ForeignKeyReconciliationPort",
        "ForeignKeyReconciliationRequest",
        "ForeignKeyReconciliationResult",
    ),
    "bioetl.domain.ports.workflow_row_reconciliation": (
        "RowReconciliationConfig",
        "RowReconciliationConfigError",
        "RowReconciliationError",
        "RowReconciliationExecutionError",
        "RowReconciliationLayer",
        "RowReconciliationMissingColumnError",
        "RowReconciliationPort",
        "RowReconciliationResult",
        "RowReconciliationTypePolicy",
        "RowReconciliationTypePolicyError",
    ),
}

_EXPORT_MODULES = {
    export_name: module_name
    for module_name, export_names in _EXPORT_GROUPS.items()
    for export_name in export_names
}

__all__ = list(_EXPORT_MODULES)


def __getattr__(name: str) -> object:  # pragma: no cover
    if TYPE_CHECKING:
        raise AttributeError
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
