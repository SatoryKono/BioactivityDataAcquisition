# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
from __future__ import annotations

import pytest

from bioetl.application.services.control_plane import (
    RunLedgerService as RunLedgerServicePackage,
)
from bioetl.application.services.control_plane import (
    RunManifestInspectionService as RunManifestInspectionServicePackage,
)
from bioetl.application.services.control_plane import (
    RunManifestService as RunManifestServicePackage,
)
from bioetl.application.services.control_plane.manifest.service import (
    RunManifestService,
)
from bioetl.application.services.control_plane.ledger.service import (
    RunLedgerService,
)
from bioetl.application.services.control_plane.manifest.inspection_service import (
    RunManifestInspectionService,
)
from bioetl.application.services.execution import (
    CliRunOrchestrationService as CliRunOrchestrationServicePackage,
)
from bioetl.application.services.execution.cli_run_orchestration_service import (
    CliRunOrchestrationService,
)
from bioetl.application.services.execution import (
    PipelineRunnerService as PipelineRunnerServicePackage,
)
from bioetl.application.services.execution import (
    RunExecutionRequest as RunExecutionRequestPackage,
)
from bioetl.application.services.execution.cli_run_orchestration_models import (
    RunExecutionRequest,
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


pytestmark = pytest.mark.unit


def test_legacy_control_plane_facades_point_to_canonical_package() -> None:
    assert RunManifestServicePackage is RunManifestService
    assert RunManifestInspectionServicePackage is RunManifestInspectionService
    assert RunLedgerServicePackage is RunLedgerService


def test_legacy_lineage_facades_point_to_canonical_package() -> None:
    assert MetadataCoordinatorPackage is MetadataCoordinator
    assert LineageInspectionServicePackage is LineageInspectionService


def test_legacy_execution_facades_point_to_canonical_package() -> None:
    assert PipelineRunnerServicePackage is PipelineRunnerService
    assert CliRunOrchestrationServicePackage is CliRunOrchestrationService
    assert RunExecutionRequestPackage is RunExecutionRequest
