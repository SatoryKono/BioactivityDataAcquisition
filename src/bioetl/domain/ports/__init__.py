"""Port interfaces (Protocols) for dependency inversion.

Implements RULES.md §1.1 - Ports & Adapters architecture.
This facade preserves historical ``from bioetl.domain.ports import X`` imports
without eagerly importing every port submodule during package initialization.
"""

from __future__ import annotations

from importlib import import_module

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
}

_EXPORT_MODULES = {
    export_name: module_name
    for module_name, export_names in _EXPORT_GROUPS.items()
    for export_name in export_names
}

__all__ = list(_EXPORT_MODULES)


def __getattr__(name: str) -> object:
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
