from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.services.audit_inspection_service import (
    AuditInspectionResult,
)
from bioetl.application.services.checkpoint_service import CheckpointInfo
from bioetl.application.services.observability_workflow_service import (
    ObservabilityWorkflowService,
)


@pytest.fixture
def audit_service() -> MagicMock:
    service = MagicMock()
    service.inspect_run = AsyncMock(
        return_value=AuditInspectionResult(
            query={"run_id": "run-1", "limit": 5},
            entries=(),
        )
    )
    return service


@pytest.fixture
def checkpoint_service() -> MagicMock:
    service = MagicMock()
    service.get_checkpoint = AsyncMock(return_value=None)
    return service


@pytest.fixture
def run_manifest_service() -> MagicMock:
    service = MagicMock()
    service.show.return_value = MagicMock(to_dict=lambda: {"manifest": "ok"})
    return service


@pytest.fixture
def service(
    audit_service: MagicMock,
    checkpoint_service: MagicMock,
    run_manifest_service: MagicMock,
) -> ObservabilityWorkflowService:
    return ObservabilityWorkflowService(
        audit_service=audit_service,
        checkpoint_service=checkpoint_service,
        run_manifest_service=run_manifest_service,
    )


@pytest.mark.asyncio
async def test_inspect_audit_run_returns_manifest_context(
    service: ObservabilityWorkflowService,
    audit_service: MagicMock,
    run_manifest_service: MagicMock,
) -> None:
    result = await service.inspect_audit_run("run-1", limit=5)

    assert result.run_id == "run-1"
    assert result.run_manifest is run_manifest_service.show.return_value
    audit_service.inspect_run.assert_awaited_once_with("run-1", limit=5)
    run_manifest_service.show.assert_called_once_with("run-1")


@pytest.mark.asyncio
async def test_inspect_checkpoint_workflow_uses_checkpoint_run_id_when_missing(
    service: ObservabilityWorkflowService,
    audit_service: MagicMock,
    checkpoint_service: MagicMock,
    run_manifest_service: MagicMock,
) -> None:
    checkpoint_service.get_checkpoint.return_value = CheckpointInfo(
        pipeline_name="chembl_activity",
        run_id="run-from-checkpoint",
        metadata={"records_processed": 42},
    )

    result = await service.inspect_checkpoint_workflow(
        "chembl_activity",
        audit_limit=11,
    )

    assert result.pipeline_name == "chembl_activity"
    assert result.checkpoint is checkpoint_service.get_checkpoint.return_value
    assert result.run_manifest is run_manifest_service.show.return_value
    audit_service.inspect_run.assert_awaited_once_with(
        "run-from-checkpoint",
        limit=11,
    )
    run_manifest_service.show.assert_called_once_with("run-from-checkpoint")


@pytest.mark.asyncio
async def test_inspect_checkpoint_workflow_returns_empty_audit_when_no_run_context(
    service: ObservabilityWorkflowService,
    audit_service: MagicMock,
    checkpoint_service: MagicMock,
    run_manifest_service: MagicMock,
) -> None:
    checkpoint_service.get_checkpoint.return_value = None

    result = await service.inspect_checkpoint_workflow("chembl_activity")

    assert result.checkpoint is None
    assert result.audit.entries == ()
    assert result.run_manifest is None
    audit_service.inspect_run.assert_not_called()
    run_manifest_service.show.assert_not_called()
