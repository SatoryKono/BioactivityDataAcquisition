from __future__ import annotations

from unittest import mock

import pytest

from bioetl.application.services.audit_inspection_service import AuditInspectionResult
from bioetl.application.services.checkpoint_service import CheckpointInfo
from bioetl.application.services.observability_workflow_service import (
    ObservabilityWorkflowService,
)


@pytest.mark.asyncio
async def test_inspect_audit_run_returns_manifest_context() -> None:
    audit_result = AuditInspectionResult(query={"run_id": "abc"}, entries=())
    audit_service = mock.AsyncMock()
    audit_service.inspect_run.return_value = audit_result
    run_manifest_service = mock.Mock()
    run_manifest_service.show.return_value = manifest = mock.Mock()

    service = ObservabilityWorkflowService(
        audit_service=audit_service,
        checkpoint_service=mock.AsyncMock(),
        run_manifest_service=run_manifest_service,
    )

    result = await service.inspect_audit_run("abc", limit=7)

    assert result.run_id == "abc"
    assert result.audit is audit_result
    assert result.run_manifest is manifest
    audit_service.inspect_run.assert_awaited_once_with("abc", limit=7)
    run_manifest_service.show.assert_called_once_with("abc")


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
