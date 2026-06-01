"""Tests for debug adapter implementations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.domain.ports import PipelineDebugPort
from bioetl.domain.ports.runtime.pipeline_debug import (
    BreakpointHit,
    DebugAction,
    PipelineSnapshot,
    StageBreakpoint,
)
from bioetl.infrastructure.observability.debug_adapters import (
    LoggingDebugAdapter,
)


def _make_logger() -> MagicMock:
    logger = MagicMock()
    logger.info = MagicMock()
    logger.debug = MagicMock()
    return logger


def _make_hit(
    bp: StageBreakpoint = StageBreakpoint.AFTER_BRONZE,
) -> BreakpointHit:
    return BreakpointHit(
        breakpoint=bp,
        snapshot=PipelineSnapshot(stage=bp.value, records_fetched=42),
        message="test breakpoint",
    )


@pytest.mark.unit
class TestLoggingDebugAdapter:
    """Tests for LoggingDebugAdapter."""

    def test_logging_debug_adapter__satisfies_protocol__c0728c91(self) -> None:
        adapter = LoggingDebugAdapter(logger=_make_logger())
        assert isinstance(adapter, PipelineDebugPort)

    def test_all_breakpoints_enabled_by_default(self) -> None:
        adapter = LoggingDebugAdapter(logger=_make_logger())
        for bp in StageBreakpoint:
            assert adapter.is_breakpoint_enabled(bp) is True

    def test_custom_breakpoints(self) -> None:
        adapter = LoggingDebugAdapter(
            logger=_make_logger(),
            enabled_breakpoints={StageBreakpoint.AFTER_BRONZE},
        )
        assert adapter.is_breakpoint_enabled(StageBreakpoint.AFTER_BRONZE) is True
        assert adapter.is_breakpoint_enabled(StageBreakpoint.AFTER_SILVER) is False

    def test_logging_debug_adapter__returns_continue__fecc9a32(self) -> None:
        adapter = LoggingDebugAdapter(logger=_make_logger())
        action = adapter.on_breakpoint(_make_hit())
        assert action == DebugAction.CONTINUE

    def test_on_breakpoint_logs(self) -> None:
        logger = _make_logger()
        adapter = LoggingDebugAdapter(logger=logger)
        adapter.on_breakpoint(_make_hit())
        logger.info.assert_called_once()
        call_kwargs = logger.info.call_args
        assert "debug_breakpoint" in call_kwargs[0]

    def test_on_snapshot_stores_and_logs(self) -> None:
        logger = _make_logger()
        adapter = LoggingDebugAdapter(logger=logger)
        snapshot = PipelineSnapshot(stage="test", records_fetched=100)
        adapter.on_snapshot(snapshot)
        assert len(adapter._snapshots) == 1
        logger.debug.assert_called_once()
