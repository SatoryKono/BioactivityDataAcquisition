"""Lazy compatibility facade for dependency-inversion port protocols."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports.observability import (
        HealthMetricsExpositionPort as HealthMetricsExpositionPort,
    )

_EXPORT_GROUPS: dict[str, tuple[str, ...]] = {
    "bioetl.domain.ports.adr": (
        "AdrDocument",
        "AdrInfo",
        "AdrServicePort",
        "AdrIssueSeverity",
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
        "ExportJobStatus",
        "ExportRedactionProfile",
        "ExportRole",
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
        "HealthMetricsExpositionPort",
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
    "bioetl.domain.ports.stage_accounting": ("StageAccountingPort",),
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
        "ForeignKeyReconciliationAction",
        "ForeignKeyReconciliationLayer",
        "ForeignKeyReconciliationMutationMode",
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

def _build_export_modules(
    export_groups: dict[str, tuple[str, ...]],
) -> dict[str, str]:
    """Map export names to modules with fail-fast collision detection."""
    export_modules: dict[str, str] = {}
    for module_name, export_names in export_groups.items():
        for export_name in export_names:
            existing = export_modules.get(export_name)
            if existing is not None and existing != module_name:
                raise RuntimeError(
                    f"duplicate ports export {export_name!r}: "
                    f"{existing!r} and {module_name!r}"
                )
            export_modules[export_name] = module_name
    return export_modules


_EXPORT_MODULES = _build_export_modules(_EXPORT_GROUPS)

__all__ = [*_EXPORT_MODULES]


def __getattr__(name: str) -> object:  # pragma: no cover
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
