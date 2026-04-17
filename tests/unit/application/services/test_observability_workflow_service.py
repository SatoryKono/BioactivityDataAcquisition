from __future__ import annotations

from unittest import mock

import pytest

from bioetl.application.services.audit_inspection_service import AuditInspectionResult
from bioetl.application.services.checkpoint_service import CheckpointInfo
from bioetl.application.services.observability_workflow_service import (
    ObservabilityWorkflowService,
)


def _make_mock_tracer() -> mock.MagicMock:
    """Create a tracing port mock with an inspectable span context."""
    mock_span = mock.MagicMock()
    mock_span.__enter__ = mock.MagicMock(return_value=mock_span)
    mock_span.__exit__ = mock.MagicMock(return_value=None)
    mock_span.set_attribute = mock.MagicMock()
    mock_span.record_exception = mock.MagicMock()

    mock_otel_tracer = mock.MagicMock()
    mock_otel_tracer.start_as_current_span = mock.MagicMock(return_value=mock_span)

    mock_tracer = mock.MagicMock()
    mock_tracer.get_tracer = mock.MagicMock(return_value=mock_otel_tracer)
    mock_tracer.flush = mock.MagicMock()
    return mock_tracer


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
        tracer=_make_mock_tracer(),
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
        tracer=_make_mock_tracer(),
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
        tracer=_make_mock_tracer(),
    )

    result = await service.inspect_checkpoint_workflow(
        "chembl_activity", audit_limit=11
    )

    assert result.audit.entries == ()
    assert result.run_manifest is None
    audit_service.inspect_run.assert_not_called()


@pytest.mark.asyncio
async def test_inspect_audit_run_creates_trace_span() -> None:
    audit_result = AuditInspectionResult(query={"run_id": "abc"}, entries=())
    audit_service = mock.AsyncMock()
    audit_service.inspect_run.return_value = audit_result
    tracer = _make_mock_tracer()

    service = ObservabilityWorkflowService(
        audit_service=audit_service,
        checkpoint_service=mock.AsyncMock(),
        run_manifest_service=None,
        tracer=tracer,
    )

    await service.inspect_audit_run("abc")

    tracer.get_tracer.assert_called_once_with("bioetl.diagnostics")
    args = tracer.get_tracer.return_value.start_as_current_span.call_args
    assert args[0][0] == "diagnostics.inspect_audit_run"
