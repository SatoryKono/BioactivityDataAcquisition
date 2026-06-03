"""Unit tests for PipelineDebugService."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.application.services.pipeline_debug_service import (
    DebugAbortError,
    PipelineDebugService,
)
from bioetl.domain.ports import (
    BreakpointHit,
    DebugAction,
    PipelineSnapshot,
    StageBreakpoint,
)


class TestDebugAbortError:
    """Tests for DebugAbortError exception."""

    @pytest.mark.unit
    def test_debug_abort_error_message(self):
        """Test that DebugAbortError stores the error message."""
        error = DebugAbortError("Pipeline aborted at breakpoint after_preflight")
        assert str(error) == "Pipeline aborted at breakpoint after_preflight"


class TestPipelineDebugService:
    """Tests for PipelineDebugService."""

    @pytest.mark.unit
    def test_capture_snapshot_basic(self):
        """Test basic snapshot capture with minimal parameters."""
        mock_debug_port = MagicMock()
        mock_logger = MagicMock()
        service = PipelineDebugService(
            debug_port=mock_debug_port,
            logger=mock_logger,
        )

        snapshot = service.capture_snapshot("FETCH")

        assert snapshot.stage == "FETCH"
        assert snapshot.records_fetched == 0
        assert snapshot.records_bronze == 0
        assert snapshot.records_silver == 0
        assert snapshot.records_gold == 0
        assert snapshot.records_quarantined == 0
        assert snapshot.dq_issues == {}
        assert snapshot.sample_records == []
        assert snapshot.metadata == {}
        assert len(service.snapshots) == 1
        mock_debug_port.on_snapshot.assert_called_once_with(snapshot)

    @pytest.mark.unit
    def test_capture_snapshot_with_all_parameters(self):
        """Test snapshot capture with all parameters."""
        mock_debug_port = MagicMock()
        mock_logger = MagicMock()
        service = PipelineDebugService(
            debug_port=mock_debug_port,
            logger=mock_logger,
        )

        dq_issues = {"missing_field": 5, "type_mismatch": 2}
        sample_records = [{"id": 1, "value": "test"}]
        metadata = {"batch_id": "batch-123"}

        snapshot = service.capture_snapshot(
            "TRANSFORM",
            records_fetched=100,
            records_bronze=90,
            records_silver=85,
            records_gold=80,
            records_quarantined=10,
            dq_issues=dq_issues,
            sample_records=sample_records,
            metadata=metadata,
        )

        assert snapshot.stage == "TRANSFORM"
        assert snapshot.records_fetched == 100
        assert snapshot.records_bronze == 90
        assert snapshot.records_silver == 85
        assert snapshot.records_gold == 80
        assert snapshot.records_quarantined == 10
        assert snapshot.dq_issues == dq_issues
        assert snapshot.sample_records == sample_records
        assert snapshot.metadata == metadata
        assert len(service.snapshots) == 1

    @pytest.mark.unit
    def test_capture_snapshot_multiple_snapshots(self):
        """Test that multiple snapshots are stored in order."""
        mock_debug_port = MagicMock()
        mock_logger = MagicMock()
        service = PipelineDebugService(
            debug_port=mock_debug_port,
            logger=mock_logger,
        )

        snapshot1 = service.capture_snapshot("FETCH")
        snapshot2 = service.capture_snapshot("TRANSFORM")
        snapshot3 = service.capture_snapshot("LOAD")

        assert len(service.snapshots) == 3
        assert service.snapshots[0] == snapshot1
        assert service.snapshots[1] == snapshot2
        assert service.snapshots[2] == snapshot3

    @pytest.mark.unit
    def test_check_breakpoint_disabled(self):
        """Test that disabled breakpoints return CONTINUE."""
        mock_debug_port = MagicMock()
        mock_debug_port.is_breakpoint_enabled.return_value = False
        mock_logger = MagicMock()
        service = PipelineDebugService(
            debug_port=mock_debug_port,
            logger=mock_logger,
        )

        snapshot = PipelineSnapshot(
            stage="FETCH",
            records_fetched=10,
            records_bronze=10,
            records_silver=10,
            records_gold=10,
            records_quarantined=0,
            dq_issues={},
            sample_records=[],
            metadata={},
        )

        action = service.check_breakpoint(StageBreakpoint.AFTER_BRONZE, snapshot)

        assert action == DebugAction.CONTINUE
        mock_debug_port.is_breakpoint_enabled.assert_called_once_with(StageBreakpoint.AFTER_BRONZE)
        mock_debug_port.on_breakpoint.assert_not_called()

    @pytest.mark.unit
    def test_check_breakpoint_enabled_continue(self):
        """Test that enabled breakpoints with CONTINUE action work correctly."""
        mock_debug_port = MagicMock()
        mock_debug_port.is_breakpoint_enabled.return_value = True
        mock_debug_port.on_breakpoint.return_value = DebugAction.CONTINUE
        mock_logger = MagicMock()
        service = PipelineDebugService(
            debug_port=mock_debug_port,
            logger=mock_logger,
        )

        snapshot = PipelineSnapshot(
            stage="FETCH",
            records_fetched=10,
            records_bronze=10,
            records_silver=10,
            records_gold=10,
            records_quarantined=0,
            dq_issues={},
            sample_records=[],
            metadata={},
        )

        action = service.check_breakpoint(StageBreakpoint.AFTER_SILVER, snapshot, "Test message")

        assert action == DebugAction.CONTINUE
        mock_debug_port.on_breakpoint.assert_called_once()
        hit_arg = mock_debug_port.on_breakpoint.call_args[0][0]
        assert isinstance(hit_arg, BreakpointHit)
        assert hit_arg.breakpoint == StageBreakpoint.AFTER_SILVER
        assert hit_arg.snapshot == snapshot
        assert hit_arg.message == "Test message"
        mock_logger.info.assert_called_once()
        mock_logger.debug.assert_called_once()

    @pytest.mark.unit
    def test_check_breakpoint_enabled_abort(self):
        """Test that enabled breakpoints with ABORT action raise DebugAbortError."""
        mock_debug_port = MagicMock()
        mock_debug_port.is_breakpoint_enabled.return_value = True
        mock_debug_port.on_breakpoint.return_value = DebugAction.ABORT
        mock_logger = MagicMock()
        service = PipelineDebugService(
            debug_port=mock_debug_port,
            logger=mock_logger,
        )

        snapshot = PipelineSnapshot(
            stage="FETCH",
            records_fetched=10,
            records_bronze=10,
            records_silver=10,
            records_gold=10,
            records_quarantined=0,
            dq_issues={},
            sample_records=[],
            metadata={},
        )

        with pytest.raises(DebugAbortError) as exc_info:
            service.check_breakpoint(StageBreakpoint.AFTER_GOLD, snapshot)

        assert "Pipeline aborted at breakpoint after_gold" in str(exc_info.value)
        mock_debug_port.on_breakpoint.assert_called_once()

    @pytest.mark.unit
    def test_check_breakpoint_enabled_inspect(self):
        """Test that enabled breakpoints with INSPECT action work correctly."""
        mock_debug_port = MagicMock()
        mock_debug_port.is_breakpoint_enabled.return_value = True
        mock_debug_port.on_breakpoint.return_value = DebugAction.INSPECT
        mock_logger = MagicMock()
        service = PipelineDebugService(
            debug_port=mock_debug_port,
            logger=mock_logger,
        )

        snapshot = PipelineSnapshot(
            stage="FETCH",
            records_fetched=10,
            records_bronze=10,
            records_silver=10,
            records_gold=10,
            records_quarantined=0,
            dq_issues={},
            sample_records=[],
            metadata={},
        )

        action = service.check_breakpoint(StageBreakpoint.AFTER_DQ, snapshot)

        assert action == DebugAction.INSPECT
        mock_debug_port.on_breakpoint.assert_called_once()

    @pytest.mark.unit
    def test_snapshots_property_returns_copy(self):
        """Test that snapshots property returns a copy of the list."""
        mock_debug_port = MagicMock()
        mock_logger = MagicMock()
        service = PipelineDebugService(
            debug_port=mock_debug_port,
            logger=mock_logger,
        )

        service.capture_snapshot("FETCH")
        snapshots_copy = service.snapshots

        # Modify the copy
        snapshots_copy.append(None)

        # Original should be unchanged
        assert len(service.snapshots) == 1
        assert None not in service.snapshots

    @pytest.mark.unit
    def test_get_latest_snapshot_with_snapshots(self):
        """Test get_latest_snapshot returns the most recent snapshot."""
        mock_debug_port = MagicMock()
        mock_logger = MagicMock()
        service = PipelineDebugService(
            debug_port=mock_debug_port,
            logger=mock_logger,
        )

        service.capture_snapshot("FETCH")
        service.capture_snapshot("TRANSFORM")
        service.capture_snapshot("LOAD")

        latest = service.get_latest_snapshot()
        assert latest is not None
        assert latest.stage == "LOAD"

    @pytest.mark.unit
    def test_get_latest_snapshot_without_snapshots(self):
        """Test get_latest_snapshot returns None when no snapshots."""
        mock_debug_port = MagicMock()
        mock_logger = MagicMock()
        service = PipelineDebugService(
            debug_port=mock_debug_port,
            logger=mock_logger,
        )

        latest = service.get_latest_snapshot()
        assert latest is None

    @pytest.mark.unit
    def test_clear_snapshots(self):
        """Test clear_snapshots removes all snapshots."""
        mock_debug_port = MagicMock()
        mock_logger = MagicMock()
        service = PipelineDebugService(
            debug_port=mock_debug_port,
            logger=mock_logger,
        )

        service.capture_snapshot("FETCH")
        service.capture_snapshot("TRANSFORM")
        assert len(service.snapshots) == 2

        service.clear_snapshots()
        assert len(service.snapshots) == 0
        assert service.get_latest_snapshot() is None