"""Tests for PipelineDebugService."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.application.services.pipeline_debug_service import (
    DebugAbortError,
    PipelineDebugService,
)
from bioetl.domain.ports.noop import NoOpDebug
from bioetl.domain.ports.runtime.pipeline_debug import (
    BreakpointHit,
    DebugAction,
    PipelineSnapshot,
    StageBreakpoint,
)


def _make_logger() -> MagicMock:
    """Create a mock LoggerPort."""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.debug = MagicMock()
    return logger


@pytest.mark.unit
class TestPipelineDebugService:
    """Tests for PipelineDebugService."""

    def test_capture_snapshot_stores_snapshot(self) -> None:
        service = PipelineDebugService(debug_port=NoOpDebug(), logger=_make_logger())
        snapshot = service.capture_snapshot(
            "after_bronze", records_fetched=100, records_bronze=95
        )
        assert snapshot.stage == "after_bronze"
        assert snapshot.records_fetched == 100
        assert snapshot.records_bronze == 95
        assert len(service.snapshots) == 1

    def test_capture_multiple_snapshots(self) -> None:
        service = PipelineDebugService(debug_port=NoOpDebug(), logger=_make_logger())
        service.capture_snapshot("after_preflight")
        service.capture_snapshot("after_bronze", records_fetched=50)
        service.capture_snapshot("after_silver", records_silver=45)
        assert len(service.snapshots) == 3
        assert service.get_latest_snapshot() is not None
        assert service.get_latest_snapshot().stage == "after_silver"  # type: ignore[union-attr]

    def test_get_latest_snapshot_empty(self) -> None:
        service = PipelineDebugService(debug_port=NoOpDebug(), logger=_make_logger())
        assert service.get_latest_snapshot() is None

    def test_clear_snapshots(self) -> None:
        service = PipelineDebugService(debug_port=NoOpDebug(), logger=_make_logger())
        service.capture_snapshot("stage1")
        service.capture_snapshot("stage2")
        service.clear_snapshots()
        assert len(service.snapshots) == 0

    def test_check_breakpoint_with_noop_continues(self) -> None:
        service = PipelineDebugService(debug_port=NoOpDebug(), logger=_make_logger())
        snapshot = PipelineSnapshot(stage="test")
        action = service.check_breakpoint(StageBreakpoint.AFTER_BRONZE, snapshot)
        assert action == DebugAction.CONTINUE

    def test_check_breakpoint_abort_raises(self) -> None:
        mock_port = MagicMock()
        mock_port.is_breakpoint_enabled.return_value = True
        mock_port.on_breakpoint.return_value = DebugAction.ABORT

        service = PipelineDebugService(debug_port=mock_port, logger=_make_logger())
        snapshot = PipelineSnapshot(stage="test")
        with pytest.raises(DebugAbortError, match="breakpoint"):
            service.check_breakpoint(StageBreakpoint.AFTER_SILVER, snapshot)

    def test_check_breakpoint_enabled_calls_port(self) -> None:
        mock_port = MagicMock()
        mock_port.is_breakpoint_enabled.return_value = True
        mock_port.on_breakpoint.return_value = DebugAction.CONTINUE

        service = PipelineDebugService(debug_port=mock_port, logger=_make_logger())
        snapshot = PipelineSnapshot(stage="test", records_fetched=42)
        action = service.check_breakpoint(
            StageBreakpoint.AFTER_BRONZE, snapshot, message="test msg"
        )
        assert action == DebugAction.CONTINUE
        mock_port.on_breakpoint.assert_called_once()
        hit: BreakpointHit = mock_port.on_breakpoint.call_args[0][0]
        assert hit.breakpoint == StageBreakpoint.AFTER_BRONZE
        assert hit.snapshot.records_fetched == 42
        assert hit.message == "test msg"

    def test_snapshots_returns_copy(self) -> None:
        service = PipelineDebugService(debug_port=NoOpDebug(), logger=_make_logger())
        service.capture_snapshot("stage1")
        snapshots = service.snapshots
        snapshots.clear()
        assert len(service.snapshots) == 1  # Original unaffected


@pytest.mark.unit
class TestNoOpDebug:
    """Tests for NoOpDebug null-object implementation."""

    def test_breakpoint_never_enabled(self) -> None:
        noop = NoOpDebug()
        for bp in StageBreakpoint:
            assert noop.is_breakpoint_enabled(bp) is False

    def test_on_breakpoint_returns_continue(self) -> None:
        noop = NoOpDebug()
        hit = BreakpointHit(
            breakpoint=StageBreakpoint.AFTER_BRONZE,
            snapshot=PipelineSnapshot(stage="test"),
        )
        assert noop.on_breakpoint(hit) == DebugAction.CONTINUE

    def test_on_snapshot_noop(self) -> None:
        noop = NoOpDebug()
        snapshot = PipelineSnapshot(stage="test", records_fetched=100)
        noop.on_snapshot(snapshot)  # Should not raise

    def test_satisfies_protocol(self) -> None:
        from bioetl.domain.ports import PipelineDebugPort

        noop = NoOpDebug()
        assert isinstance(noop, PipelineDebugPort)


@pytest.mark.unit
class TestPipelineSnapshot:
    """Tests for PipelineSnapshot value object."""

    def test_defaults(self) -> None:
        snapshot = PipelineSnapshot(stage="test")
        assert snapshot.records_fetched == 0
        assert snapshot.records_bronze == 0
        assert snapshot.records_silver == 0
        assert snapshot.records_gold == 0
        assert snapshot.records_quarantined == 0
        assert snapshot.dq_issues == {}
        assert snapshot.sample_records == []
        assert snapshot.metadata == {}

    def test_immutable(self) -> None:
        snapshot = PipelineSnapshot(stage="test", records_fetched=10)
        with pytest.raises((AttributeError, TypeError)):
            snapshot.records_fetched = 99  # type: ignore[misc]

    def test_with_data(self) -> None:
        snapshot = PipelineSnapshot(
            stage="after_silver",
            records_fetched=1000,
            records_silver=950,
            records_quarantined=50,
            dq_issues={"missing_field": 30, "invalid_format": 20},
            sample_records=[{"id": "CHEMBL1"}],
            metadata={"provider": "chembl"},
        )
        assert snapshot.dq_issues["missing_field"] == 30
        assert len(snapshot.sample_records) == 1


@pytest.mark.unit
class TestStageBreakpoint:
    """Tests for StageBreakpoint enum."""

    def test_all_values(self) -> None:
        expected = {
            "after_preflight",
            "after_bronze",
            "after_silver",
            "after_gold",
            "after_dq",
            "on_error",
            "on_quarantine",
        }
        assert {bp.value for bp in StageBreakpoint} == expected

    def test_from_string(self) -> None:
        bp = StageBreakpoint("after_bronze")
        assert bp == StageBreakpoint.AFTER_BRONZE


@pytest.mark.unit
class TestDebugAction:
    """Tests for DebugAction enum."""

    def test_all_values__test_debug_action_application_services_test_pipeline_debug_service_193(
        self,
    ) -> None:
        expected = {"continue", "skip_stage", "inspect", "abort", "dump_state"}
        assert {a.value for a in DebugAction} == expected
