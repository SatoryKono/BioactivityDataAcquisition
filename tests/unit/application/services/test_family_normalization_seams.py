from __future__ import annotations

from bioetl.application.services.cli_run_orchestration_models import (
    RunExecutionRequest as RunExecutionRequestLegacy,
)
from bioetl.application.services.cli_run_orchestration_service import (
    CliRunOrchestrationService as CliRunOrchestrationServiceLegacy,
)
from bioetl.application.services.control_plane import (
    RunLedgerService as RunLedgerServicePackage,
)
from bioetl.application.services.control_plane import (
    RunManifestInspectionService as RunManifestInspectionServicePackage,
)
from bioetl.application.services.control_plane import (
    RunManifestService as RunManifestServicePackage,
)
from bioetl.application.services.execution import (
    CliRunOrchestrationService as CliRunOrchestrationServicePackage,
)
from bioetl.application.services.execution import (
    PipelineRunnerService as PipelineRunnerServicePackage,
)
from bioetl.application.services.execution import (
    RunExecutionRequest as RunExecutionRequestPackage,
)
from bioetl.application.services.execution.pipeline_runner_service import (
    PipelineRunnerService,
)
from bioetl.application.services.lineage import (
    LineageInspectionService as LineageInspectionServicePackage,
)
from bioetl.application.services.lineage import (
    MetadataCoordinator as MetadataCoordinatorPackage,
)
from bioetl.application.services.lineage.lineage_inspection_service import (
    LineageInspectionService,
)
from bioetl.application.services.lineage.metadata_coordinator import (
    MetadataCoordinator,
)
from bioetl.application.services.lineage_inspection_service import (
    LineageInspectionService as LineageInspectionServiceLegacy,
)
from bioetl.application.services.metadata_coordinator import (
    MetadataCoordinator as MetadataCoordinatorLegacy,
)
from bioetl.application.services.pipeline_runner_service import (
    PipelineRunnerService as PipelineRunnerServiceLegacy,
)
from bioetl.application.services.run_ledger_service import (
    RunLedgerService as RunLedgerServiceLegacy,
)
from bioetl.application.services.run_manifest_inspection_service import (
    RunManifestInspectionService as RunManifestInspectionServiceLegacy,
)
from bioetl.application.services.run_manifest_service import (
    RunManifestService as RunManifestServiceLegacy,
)


def test_legacy_control_plane_facades_point_to_canonical_package() -> None:
    assert RunManifestServiceLegacy is RunManifestServicePackage
    assert RunManifestInspectionServiceLegacy is RunManifestInspectionServicePackage
    assert RunLedgerServiceLegacy is RunLedgerServicePackage


def test_legacy_lineage_facades_point_to_canonical_package() -> None:
    assert MetadataCoordinatorLegacy is MetadataCoordinator
    assert MetadataCoordinatorPackage is MetadataCoordinator
    assert LineageInspectionServiceLegacy is LineageInspectionService
    assert LineageInspectionServicePackage is LineageInspectionService


def test_legacy_execution_facades_point_to_canonical_package() -> None:
    assert PipelineRunnerServiceLegacy is PipelineRunnerService
    assert PipelineRunnerServicePackage is PipelineRunnerService
    assert CliRunOrchestrationServiceLegacy is CliRunOrchestrationServicePackage
    assert RunExecutionRequestLegacy is RunExecutionRequestPackage
