from __future__ import annotations

from __future__ import annotations

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
        audit_service=audit_service,
        run_manifest_service=run_manifest_service,
    )

    result = await service.inspect_audit_run("abc", limit=7)

    assert result.run_id == "abc"
    assert result.audit is audit_result
    assert result.run_manifest is manifest
    audit_service.inspect_run.assert_awaited_once_with("abc", limit=7)
    run_manifest_service.show.assert_called_once_with("abc")


@pytest.mark.asyncio
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
async def test_checkpoint_workflow_derives_run_id_from_checkpoint() -> None:
    checkpoint_service = mock.AsyncMock()
    checkpoint_service.get_checkpoint.return_value = CheckpointInfo(
        pipeline_name="chembl_activity",
        run_id="run-123",
        metadata={"records_processed": 5},
    )
    audit_result = AuditInspectionResult(query={"run_id": "run-123"}, entries=())
    audit_service = mock.AsyncMock()
    audit_service.inspect_run.return_value = audit_result
    run_manifest_service = mock.Mock()
    run_manifest_service.show.return_value = manifest = mock.Mock()

    service = ObservabilityWorkflowService(
        audit_service=audit_service,
        checkpoint_service=checkpoint_service,
        run_manifest_service=run_manifest_service,
    )

    result = await service.inspect_checkpoint_workflow("chembl_activity", audit_limit=9)

    assert result.pipeline_name == "chembl_activity"
    assert result.audit is audit_result
    assert result.run_manifest is manifest
    audit_service.inspect_run.assert_awaited_once_with("run-123", limit=9)
    run_manifest_service.show.assert_called_once_with("run-123")
    checkpoint_service.get_checkpoint.return_value = CheckpointInfo(
        pipeline_name="chembl_activity",
    )
    audit_result = AuditInspectionResult(query={"run_id": "run-123"}, entries=())
    audit_service = mock.AsyncMock()
    audit_service.inspect_run.return_value = audit_result
    run_manifest_service = mock.Mock()
    run_manifest_service.show.return_value = manifest = mock.Mock()

    )

    result = await service.inspect_checkpoint_workflow("chembl_activity", audit_limit=9)

    assert result.pipeline_name == "chembl_activity"


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_checkpoint_workflow_returns_empty_audit_without_run_context() -> None:
    checkpoint_service = mock.AsyncMock()
    checkpoint_service.get_checkpoint.return_value = CheckpointInfo(
        pipeline_name="chembl_activity",
        run_id=None,
        metadata={},
    )
    audit_service = mock.AsyncMock()

    service = ObservabilityWorkflowService(
        audit_service=audit_service,
        checkpoint_service=checkpoint_service,
        run_manifest_service=None,
    )

    result = await service.inspect_checkpoint_workflow("chembl_activity", audit_limit=11)

    assert result.audit.entries == ()
    assert result.run_manifest is None
    audit_service.inspect_run.assert_not_called()


    assert result.checkpoint is None
    assert result.audit.entries == ()
    assert result.run_manifest is None
    audit_service.inspect_run.assert_not_called()
    run_manifest_service.show.assert_not_called()
