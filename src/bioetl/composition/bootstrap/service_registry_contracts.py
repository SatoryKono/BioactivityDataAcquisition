"""Bootstrap-owned catalog of service registry protocol keys."""

from __future__ import annotations

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
from bioetl.domain.ports import AdrServicePort, QuarantinePort

__all__ = [
    "AdrServicePort",
    "AuditInspectionServiceProtocol",
    "BronzeCleanupServiceProtocol",
    "CheckpointServiceProtocol",
    "ConfigServiceProtocol",
    "ContractMigrationServiceProtocol",
    "ExportServiceProtocol",
    "ForensicRunDiffServiceProtocol",
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
    "VacuumServiceProtocol",
    "WorkflowInspectionServiceProtocol",
]
