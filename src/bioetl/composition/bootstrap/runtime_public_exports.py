"""Shared bootstrap runtime and service-registry contract catalogs.

This keeps the curated bootstrap package root and the runtime package root
aligned without duplicating long literal export tables.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.ports.control_plane import (
    ForensicRunDiffServiceProtocol,
    HistoricalReplayClosureServiceProtocol,
    HistoricalReplayCorpusServiceProtocol,
    HistoricalReplayUniverseServiceProtocol,
    LineageInspectionServiceProtocol,
    RunManifestInspectionServiceProtocol,
    WorkflowInspectionServiceProtocol,
)
from bioetl.application.ports.health import HealthServiceProtocol
from bioetl.application.ports.metrics import MetricsService
from bioetl.application.ports.operations import (
    AuditInspectionServiceProtocol,
    CheckpointServiceProtocol,
    ConfigServiceProtocol,
    ContractMigrationServiceProtocol,
    ExportServiceProtocol,
    LockServiceProtocol,
    ObservabilityWorkflowServiceProtocol,
    VacuumServiceProtocol,
)
from bioetl.composition.contracts.factories import (
    HealthServerDependenciesFactoryProtocol,
    PipelineRunnerServiceFactoryProtocol,
    QuarantineServiceFactoryProtocol,
)
from bioetl.composition.contracts.health import BronzeCleanupServiceProtocol
from bioetl.domain.ports import (
    AdrServicePort,
    GoldFilterCallback,
    GoldTransformCallback,
    QuarantinePort,
    TransformCallback,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        BronzeDQConfigPort as BronzeDQConfigPort,
        GoldDQConfigPort as GoldDQConfigPort,
        SilverDQConfigPort as SilverDQConfigPort,
    )

__all__ = [
    "BOOTSTRAP_ROOT_EXPORT_NAMES",
    "BOOTSTRAP_ROOT_PUBLIC_EXPORTS",
    "RUNTIME_PACKAGE_EXPORT_NAMES",
    "RUNTIME_PACKAGE_PUBLIC_EXPORTS",
    "SHARED_BOOTSTRAP_RUNTIME_EXPORTS",
    "AdrServicePort",
    "AuditInspectionServiceProtocol",
    "BronzeCleanupServiceProtocol",
    "BronzeDQConfigPort",
    "CheckpointServiceProtocol",
    "ConfigServiceProtocol",
    "ContractMigrationServiceProtocol",
    "ExportServiceProtocol",
    "ForensicRunDiffServiceProtocol",
    "GoldDQConfigPort",
    "GoldFilterCallback",
    "GoldTransformCallback",
    "HealthServerDependenciesFactoryProtocol",
    "HealthServiceProtocol",
    "HistoricalReplayClosureServiceProtocol",
    "HistoricalReplayCorpusServiceProtocol",
    "HistoricalReplayUniverseServiceProtocol",
    "LineageInspectionServiceProtocol",
    "LockServiceProtocol",
    "MetricsService",
    "ObservabilityWorkflowServiceProtocol",
    "PipelineRunnerServiceFactoryProtocol",
    "QuarantinePort",
    "QuarantineServiceFactoryProtocol",
    "RunManifestInspectionServiceProtocol",
    "SilverDQConfigPort",
    "TransformCallback",
    "VacuumServiceProtocol",
    "WorkflowInspectionServiceProtocol",
]

RUNTIME_OBSERVABILITY_MODULE = "bioetl.composition.bootstrap.runtime.observability"
RUNTIME_ASSEMBLY_MODULE = "bioetl.composition.bootstrap.runtime.assembly"

SHARED_BOOTSTRAP_RUNTIME_EXPORTS: dict[str, str] = {
    "bootstrap_composite_runner": "bioetl.composition.bootstrap.runtime.composite",
    "bootstrap_dq_monitor": RUNTIME_OBSERVABILITY_MODULE,
    "bootstrap_logger": RUNTIME_OBSERVABILITY_MODULE,
    "bootstrap_metrics": RUNTIME_OBSERVABILITY_MODULE,
    "bootstrap_observability_bundle": RUNTIME_OBSERVABILITY_MODULE,
    "bootstrap_pipeline_runner": "bioetl.composition.bootstrap.runtime.pipeline",
    "bootstrap_tracer": RUNTIME_OBSERVABILITY_MODULE,
    "load_composite_config": "bioetl.composition.bootstrap.runtime.composite",
    "maybe_start_metrics_server": RUNTIME_OBSERVABILITY_MODULE,
}

BOOTSTRAP_ROOT_PUBLIC_EXPORTS: dict[str, tuple[str, str]] = {
    name: (module_name, name)
    for name, module_name in SHARED_BOOTSTRAP_RUNTIME_EXPORTS.items()
}
BOOTSTRAP_ROOT_PUBLIC_EXPORTS["load_pipeline_config"] = (
    "bioetl.infrastructure.config.pipeline_config_api",
    "load_pipeline_config",
)

RUNTIME_PACKAGE_PUBLIC_EXPORTS: dict[str, str] = {
    **SHARED_BOOTSTRAP_RUNTIME_EXPORTS,
    "MetricsServerError": RUNTIME_OBSERVABILITY_MODULE,
    "assemble_filter_config": RUNTIME_ASSEMBLY_MODULE,
    "assemble_runtime_config": RUNTIME_ASSEMBLY_MODULE,
    "apply_runtime_compatibility_patches": (
        "bioetl.composition.bootstrap.runtime.pipeline"
    ),
    "assemble_vacuum_settings": RUNTIME_ASSEMBLY_MODULE,
    "bootstrap_pipeline_runner_service": (
        "bioetl.composition.bootstrap.runtime.pipeline_runner_service_bootstrap"
    ),
    "validate_observability_preflight": RUNTIME_OBSERVABILITY_MODULE,
}

BOOTSTRAP_ROOT_EXPORT_NAMES: tuple[str, ...] = (
    *SHARED_BOOTSTRAP_RUNTIME_EXPORTS,
    "load_pipeline_config",
)

RUNTIME_PACKAGE_EXPORT_NAMES: tuple[str, ...] = (
    "MetricsServerError",
    "apply_runtime_compatibility_patches",
    "assemble_filter_config",
    "assemble_runtime_config",
    "assemble_vacuum_settings",
    *SHARED_BOOTSTRAP_RUNTIME_EXPORTS,
    "bootstrap_pipeline_runner_service",
    "composite_control_plane_builder",
    "validate_observability_preflight",
)
