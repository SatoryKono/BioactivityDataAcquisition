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
"""Unit tests for CheckpointService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.services.checkpoint.checkpoint_service import (
    CheckpointInfo,
    CheckpointService,
)
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite


def _assert_metric_labels(
    checkpoint_service: CheckpointService,
    *,
    operation: str,
    status: str,
) -> None:
    """Assert the latest checkpoint admin metric pair uses bounded labels."""
    assert checkpoint_service.metrics.increment_counter.call_args_list[-1].args == (
        "bioetl_checkpoint_operator_operations_total",
        1,
    )
    assert checkpoint_service.metrics.increment_counter.call_args_list[-1].kwargs == {
        "labels": {"operation": operation, "status": status}
    }
    assert (
        checkpoint_service.metrics.observe_histogram.call_args_list[-1].args[0]
        == "bioetl_checkpoint_operator_duration_seconds"
    )
    assert checkpoint_service.metrics.observe_histogram.call_args_list[-1].kwargs == {
        "labels": {"operation": operation, "status": status}
    }


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    logger.info = MagicMock()
    logger.debug = MagicMock()
    logger.warning = MagicMock()
    return logger


@pytest.fixture
def mock_checkpoint_port():
    """Create a mock checkpoint port."""
    port = MagicMock()
    port.list_all = AsyncMock(return_value=[])
    port.load = AsyncMock(return_value=None)
    port.delete = AsyncMock()
    port.aclose = AsyncMock()
    return port


@pytest.fixture
def checkpoint_service(mock_checkpoint_port, mock_logger):
    """Create a CheckpointService instance."""
    metrics = MagicMock()
    metrics.increment_counter = MagicMock()
    metrics.observe_histogram = MagicMock()
    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=None)
    mock_span.set_attribute = MagicMock()
    mock_span.record_exception = MagicMock()
    otel_tracer = MagicMock()
    otel_tracer.start_as_current_span = MagicMock(return_value=mock_span)
    tracer = MagicMock()
    tracer.get_tracer = MagicMock(return_value=otel_tracer)
    tracer.flush = MagicMock()
    return CheckpointService(
        checkpoint_port=mock_checkpoint_port,
        logger=mock_logger,
        metrics=metrics,
        tracer=tracer,
    )


@pytest.mark.unit
class TestCheckpointInfo:
    """Test CheckpointInfo dataclass."""

    def test_checkpoint_info_creation(self):
        """Test CheckpointInfo can be created."""
        info = CheckpointInfo(
            pipeline_name="test_pipeline",
            run_id="12345",
            metadata={"records_processed": 100},
        )

        assert info.pipeline_name == "test_pipeline"
        assert info.run_id == "12345"
        assert info.metadata == {"records_processed": 100}

    def test_checkpoint_info_with_none_run_id(self):
        """Test CheckpointInfo with None run_id."""
        info = CheckpointInfo(
            pipeline_name="test_pipeline",
            run_id=None,
            metadata={},
        )

        assert info.run_id is None


@pytest.mark.unit
class TestCheckpointServiceListCheckpoints:
    """Test CheckpointService.list_checkpoints method."""

    @pytest.mark.asyncio
    async def test_list_checkpoints_empty(
        self, checkpoint_service, mock_checkpoint_port
    ):
        """Test listing checkpoints when none exist."""
        mock_checkpoint_port.list_all.return_value = []

        result = await checkpoint_service.list_checkpoints()

        assert result == []
        mock_checkpoint_port.list_all.assert_called_once()
        checkpoint_service.metrics.increment_counter.assert_called_with(
            "bioetl_checkpoint_operator_operations_total",
            1,
            labels={"operation": "list", "status": "success"},
        )
        checkpoint_service.metrics.observe_histogram.assert_called_with(
            "bioetl_checkpoint_operator_duration_seconds",
            pytest.approx(0.0, abs=1.0),
            labels={"operation": "list", "status": "success"},
        )

    @pytest.mark.asyncio
    async def test_list_checkpoints_with_data(
        self, checkpoint_service, mock_checkpoint_port
    ):
        """Test listing checkpoints with existing data."""
        run_id = deterministic_uuid_from_callsite("checkpoint-service")
        mock_checkpoint_port.list_all.return_value = ["pipeline1", "pipeline2"]
        mock_checkpoint_port.load.side_effect = [
            (run_id, {"records_processed": 100}),
            (run_id, {"records_processed": 200}),
        ]

        result = await checkpoint_service.list_checkpoints()

        assert len(result) == 2
        assert result[0].pipeline_name == "pipeline1"
        assert result[0].metadata == {"records_processed": 100}
        assert result[1].pipeline_name == "pipeline2"
        assert result[1].metadata == {"records_processed": 200}

    @pytest.mark.asyncio
    async def test_list_checkpoints_with_unloadable(
        self, checkpoint_service, mock_checkpoint_port
    ):
        """Test listing checkpoints when some can't be loaded."""
        run_id = deterministic_uuid_from_callsite("checkpoint-service")
        mock_checkpoint_port.list_all.return_value = ["pipeline1", "pipeline2"]
        mock_checkpoint_port.load.side_effect = [
            (run_id, {"records_processed": 100}),
            None,  # Pipeline2 checkpoint can't be loaded
        ]

        result = await checkpoint_service.list_checkpoints()

        assert len(result) == 2
        assert result[0].run_id == str(run_id)
        assert result[1].run_id is None
        assert result[1].metadata == {}

    @pytest.mark.asyncio
    async def test_list_checkpoints_failure_records_failed_metrics(
        self, checkpoint_service, mock_checkpoint_port
    ):
        """List failures should emit a bounded failed milestone outcome."""
        mock_checkpoint_port.list_all.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            await checkpoint_service.list_checkpoints()

        _assert_metric_labels(
            checkpoint_service,
            operation="list",
            status="failed",
        )


@pytest.mark.unit
class TestCheckpointServiceGetCheckpoint:
    """Test CheckpointService.get_checkpoint method."""

    @pytest.mark.asyncio
    async def test_get_checkpoint_not_found(
        self, checkpoint_service, mock_checkpoint_port
    ):
        """Test getting a checkpoint that doesn't exist."""
        mock_checkpoint_port.load.return_value = None

        result = await checkpoint_service.get_checkpoint("nonexistent")

        assert result is None
        mock_checkpoint_port.load.assert_called_once_with("nonexistent")
        _assert_metric_labels(
            checkpoint_service,
            operation="get",
            status="missing",
        )

    @pytest.mark.asyncio
    async def test_get_checkpoint_found(self, checkpoint_service, mock_checkpoint_port):
        """Test getting an existing checkpoint."""
        run_id = deterministic_uuid_from_callsite("checkpoint-service")
        mock_checkpoint_port.load.return_value = (run_id, {"records_processed": 100})

        result = await checkpoint_service.get_checkpoint("pipeline1")

        assert result is not None
        assert result.pipeline_name == "pipeline1"
        assert result.run_id == str(run_id)
        assert result.metadata == {"records_processed": 100}
        _assert_metric_labels(
            checkpoint_service,
            operation="get",
            status="success",
        )

    @pytest.mark.asyncio
    async def test_get_checkpoint_creates_trace_span(
        self, checkpoint_service, mock_checkpoint_port
    ):
        """Checkpoint get should create a bounded admin trace span."""
        run_id = deterministic_uuid_from_callsite("checkpoint-service")
        mock_checkpoint_port.load.return_value = (run_id, {"records_processed": 100})

        await checkpoint_service.get_checkpoint("pipeline1")

        checkpoint_service.tracer.get_tracer.assert_called_once_with(
            "bioetl.checkpoint_admin"
        )
        args = checkpoint_service.tracer.get_tracer.return_value.start_as_current_span.call_args
        assert args[0][0] == "checkpoint.get"

    @pytest.mark.asyncio
    async def test_get_checkpoint_failure_records_failed_metrics(
        self, checkpoint_service, mock_checkpoint_port
    ):
        """Get failures should emit a bounded failed milestone outcome."""
        mock_checkpoint_port.load.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            await checkpoint_service.get_checkpoint("pipeline1")

        _assert_metric_labels(
            checkpoint_service,
            operation="get",
            status="failed",
        )


@pytest.mark.unit
class TestCheckpointServiceExtendedLookupCoverage:
    """Additional coverage for run/manifest lookup and tracing helpers."""

    @pytest.mark.asyncio
    async def test_get_checkpoint_for_run_found(
        self, checkpoint_service, mock_checkpoint_port
    ) -> None:
        run_id = str(deterministic_uuid_from_callsite("checkpoint-service-for-run"))
        mock_checkpoint_port.load_for_run = AsyncMock(
            return_value=(run_id, {"records_processed": 12})
        )

        result = await checkpoint_service.get_checkpoint_for_run("pipeline1", run_id)

        assert result is not None
        assert result.pipeline_name == "pipeline1"
        assert result.run_id == run_id
        assert result.metadata == {"records_processed": 12}
        _assert_metric_labels(
            checkpoint_service,
            operation="get_for_run",
            status="success",
        )

    @pytest.mark.asyncio
    async def test_get_checkpoint_for_run_missing(
        self, checkpoint_service, mock_checkpoint_port
    ) -> None:
        run_id = str(deterministic_uuid_from_callsite("checkpoint-service-for-run"))
        mock_checkpoint_port.load_for_run = AsyncMock(return_value=None)

        result = await checkpoint_service.get_checkpoint_for_run("pipeline1", run_id)

        assert result is None
        _assert_metric_labels(
            checkpoint_service,
            operation="get_for_run",
            status="missing",
        )

    @pytest.mark.asyncio
    async def test_get_checkpoint_for_manifest_id_found(
        self, checkpoint_service, mock_checkpoint_port
    ) -> None:
        run_id = str(deterministic_uuid_from_callsite("checkpoint-service-manifest"))
        mock_checkpoint_port.load_for_manifest_id = AsyncMock(
            return_value=(run_id, {"records_processed": 9})
        )

        result = await checkpoint_service.get_checkpoint_for_manifest_id(
            "pipeline1",
            "manifest-1",
        )

        assert result is not None
        assert result.pipeline_name == "pipeline1"
        assert result.run_id == run_id
        _assert_metric_labels(
            checkpoint_service,
            operation="get_for_manifest_id",
            status="success",
        )

    @pytest.mark.asyncio
    async def test_get_checkpoint_for_manifest_id_uses_payload_owner(
        self, checkpoint_service, mock_checkpoint_port
    ) -> None:
        run_id = str(deterministic_uuid_from_callsite("checkpoint-service-owner"))
        mock_checkpoint_port.load_for_manifest_id = AsyncMock(
            return_value=(run_id, {"pipeline_name": "owned_pipeline"})
        )

        result = await checkpoint_service.get_checkpoint_for_manifest_id(
            "owned_pipeline",
            "manifest-1",
        )

        assert result is not None
        assert result.pipeline_name == "owned_pipeline"

    @pytest.mark.asyncio
    async def test_get_checkpoint_for_manifest_id_rejects_owner_mismatch(
        self, checkpoint_service, mock_checkpoint_port
    ) -> None:
        run_id = str(deterministic_uuid_from_callsite("checkpoint-service-mismatch"))
        mock_checkpoint_port.load_for_manifest_id = AsyncMock(
            return_value=(run_id, {"pipeline_name": "owned_pipeline"})
        )

        with pytest.raises(ValueError, match="Checkpoint pipeline owner mismatch"):
            await checkpoint_service.get_checkpoint_for_manifest_id(
                "caller_pipeline",
                "manifest-1",
            )

    def test_trace_attributes_include_pipeline_and_extras(
        self,
        checkpoint_service,
    ) -> None:
        attributes = checkpoint_service._trace_attributes(
            operation="get",
            pipeline="chembl_activity",
            **{"bioetl.run_id": "run-1"},
        )

        assert attributes == {
            "bioetl.component": "checkpoint_service",
            "bioetl.operation": "get",
            "bioetl.pipeline": "chembl_activity",
            "bioetl.run_id": "run-1",
        }

    def test_set_trace_result_sets_success_and_extra_attributes(
        self,
        checkpoint_service,
    ) -> None:
        span = MagicMock()

        checkpoint_service._set_trace_result(
            span,
            success=False,
            attributes={
                "bioetl.checkpoint_found": True,
                "bioetl.count": 3,
            },
        )

        span.set_attribute.assert_any_call("bioetl.success", False)
        span.set_attribute.assert_any_call("bioetl.checkpoint_found", True)
        span.set_attribute.assert_any_call("bioetl.count", 3)


@pytest.mark.unit
class TestCheckpointServiceDeleteCheckpoint:
    """Test CheckpointService.delete_checkpoint method."""

    @pytest.mark.asyncio
    async def test_delete_checkpoint_not_found(
        self, checkpoint_service, mock_checkpoint_port
    ):
        """Test deleting a checkpoint that doesn't exist."""
        mock_checkpoint_port.load.return_value = None

        result = await checkpoint_service.delete_checkpoint("nonexistent")

        assert result is False
        mock_checkpoint_port.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_checkpoint_success(
        self, checkpoint_service, mock_checkpoint_port
    ):
        """Test successfully deleting a checkpoint."""
        run_id = deterministic_uuid_from_callsite("checkpoint-service")
        mock_checkpoint_port.load.return_value = (run_id, {"records_processed": 100})

        result = await checkpoint_service.delete_checkpoint("pipeline1")

        assert result is True
        mock_checkpoint_port.delete.assert_called_once_with("pipeline1")
        _assert_metric_labels(
            checkpoint_service,
            operation="delete",
            status="success",
        )

    @pytest.mark.asyncio
    async def test_delete_checkpoint_missing_records_missing_metric(
        self, checkpoint_service, mock_checkpoint_port
    ):
        """Missing checkpoint delete attempts should emit bounded missing metrics."""
        mock_checkpoint_port.load.return_value = None

        result = await checkpoint_service.delete_checkpoint("pipeline1")

        assert result is False
        _assert_metric_labels(
            checkpoint_service,
            operation="delete",
            status="missing",
        )

    @pytest.mark.asyncio
    async def test_delete_checkpoint_failure_records_failed_metrics(
        self, checkpoint_service, mock_checkpoint_port
    ):
        """Delete failures should emit a bounded failed milestone outcome."""
        run_id = deterministic_uuid_from_callsite("checkpoint-service")
        mock_checkpoint_port.load.return_value = (run_id, {"records_processed": 100})
        mock_checkpoint_port.delete.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            await checkpoint_service.delete_checkpoint("pipeline1")

        _assert_metric_labels(
            checkpoint_service,
            operation="delete",
            status="failed",
        )


@pytest.mark.unit
class TestCheckpointServiceAclose:
    """Test CheckpointService.aclose method."""

    @pytest.mark.asyncio
    async def test_service_aclose__aclose__8851e674(
        self, checkpoint_service, mock_checkpoint_port
    ):
        """Test closing the service."""
        await checkpoint_service.aclose()

        mock_checkpoint_port.aclose.assert_called_once()
