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
"""Coverage boost tests for debug_adapters.py.

Targets uncovered lines:
- InteractiveDebugAdapter (lines 45-47, 51, 55-86, 90-92)
- LoggingDebugAdapter on_snapshot with logger (lines 55+)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bioetl.domain.ports.runtime.pipeline_debug import (
    BreakpointHit,
    DebugAction,
    PipelineSnapshot,
    StageBreakpoint,
)
from bioetl.infrastructure.observability.debug_adapters import (
    InteractiveDebugAdapter,
    LoggingDebugAdapter,
)


def _make_logger() -> MagicMock:
    logger = MagicMock()
    logger.info = MagicMock()
    logger.debug = MagicMock()
    logger.warning = MagicMock()
    return logger


def _make_snapshot(
    stage: str = "after_bronze",
    records_fetched: int = 10,
    records_bronze: int = 10,
    records_silver: int = 9,
    records_gold: int = 8,
    records_quarantined: int = 1,
    dq_issues: list[str] | None = None,
    sample_records: list[dict] | None = None,
) -> PipelineSnapshot:
    return PipelineSnapshot(
        stage=stage,
        records_fetched=records_fetched,
        records_bronze=records_bronze,
        records_silver=records_silver,
        records_gold=records_gold,
        records_quarantined=records_quarantined,
        dq_issues=dq_issues,
        sample_records=sample_records,
    )


def _make_hit(
    bp: StageBreakpoint = StageBreakpoint.AFTER_BRONZE,
    message: str | None = "test msg",
    snapshot: PipelineSnapshot | None = None,
) -> BreakpointHit:
    if snapshot is None:
        snapshot = _make_snapshot()
    return BreakpointHit(
        breakpoint=bp,
        snapshot=snapshot,
        message=message,
    )


@pytest.mark.unit
class TestInteractiveDebugAdapter:
    """Tests for InteractiveDebugAdapter — covers lines 45-92."""

    def test_init_with_no_breakpoints_enables_all(self) -> None:
        """Line 45: enabled_breakpoints defaults to all breakpoints."""
        adapter = InteractiveDebugAdapter()
        for bp in StageBreakpoint:
            assert adapter.is_breakpoint_enabled(bp) is True

    def test_init_with_empty_set_uses_all_breakpoints(self) -> None:
        """Line 45: empty set is falsy, so 'or set(StageBreakpoint)' enables all."""
        # Empty set is falsy in Python, so enabled_breakpoints or set(StageBreakpoint)
        # falls back to set(StageBreakpoint) — all breakpoints enabled
        adapter = InteractiveDebugAdapter(enabled_breakpoints=set())
        for bp in StageBreakpoint:
            assert adapter.is_breakpoint_enabled(bp) is True

    def test_init_with_specific_breakpoints(self) -> None:
        """Line 45: custom enabled_breakpoints set."""
        adapter = InteractiveDebugAdapter(
            enabled_breakpoints={StageBreakpoint.AFTER_BRONZE}
        )
        assert adapter.is_breakpoint_enabled(StageBreakpoint.AFTER_BRONZE) is True
        assert adapter.is_breakpoint_enabled(StageBreakpoint.AFTER_SILVER) is False

    def test_is_breakpoint_enabled_line_51(self) -> None:
        """Line 51: breakpoint in enabled set returns True."""
        adapter = InteractiveDebugAdapter(
            enabled_breakpoints={StageBreakpoint.AFTER_SILVER}
        )
        assert adapter.is_breakpoint_enabled(StageBreakpoint.AFTER_SILVER) is True
        assert adapter.is_breakpoint_enabled(StageBreakpoint.AFTER_BRONZE) is False

    def test_on_breakpoint_with_click_prompt(self) -> None:
        """Lines 55-86: on_breakpoint prompts user and returns selected action."""
        adapter = InteractiveDebugAdapter()
        hit = _make_hit()

        with (
            patch("click.echo"),
            patch("click.prompt", return_value=DebugAction.CONTINUE.value),
        ):
            action = adapter.on_breakpoint(hit)

        assert action == DebugAction.CONTINUE

    def test_on_breakpoint_with_all_breakpoint_values(self) -> None:
        """Lines 55-86: test on_breakpoint for each DebugAction value."""
        adapter = InteractiveDebugAdapter()

        for debug_action in DebugAction:
            hit = _make_hit()
            with (
                patch("click.echo"),
                patch("click.prompt", return_value=debug_action.value),
            ):
                action = adapter.on_breakpoint(hit)
            assert action == debug_action

    def test_on_breakpoint_with_dq_issues(self) -> None:
        """Line 70-71: on_breakpoint displays DQ issues when present."""
        adapter = InteractiveDebugAdapter()
        snapshot = _make_snapshot(dq_issues=["null_rate > 5%", "schema_mismatch"])
        hit = _make_hit(snapshot=snapshot)

        echo_calls: list[str] = []
        with patch("click.echo", side_effect=lambda msg: echo_calls.append(str(msg))):
            with patch("click.prompt", return_value=DebugAction.CONTINUE.value):
                adapter.on_breakpoint(hit)

        assert any("DQ Issues" in call for call in echo_calls)

    def test_on_breakpoint_with_sample_records(self) -> None:
        """Lines 73-76: on_breakpoint displays sample records when present."""
        adapter = InteractiveDebugAdapter()
        snapshot = _make_snapshot(
            sample_records=[
                {"id": 1, "value": "test"},
                {"id": 2, "value": "foo"},
                {"id": 3, "value": "bar"},
                {"id": 4, "value": "extra"},  # Only first 3 shown
            ]
        )
        hit = _make_hit(snapshot=snapshot)

        echo_calls: list[str] = []
        with patch("click.echo", side_effect=lambda msg: echo_calls.append(str(msg))):
            with patch("click.prompt", return_value=DebugAction.CONTINUE.value):
                adapter.on_breakpoint(hit)

        assert any("Sample" in call for call in echo_calls)

    def test_on_breakpoint_without_message(self) -> None:
        """Line 60-61: message is None — skips the message echo."""
        adapter = InteractiveDebugAdapter()
        hit = _make_hit(message=None)

        echo_calls: list[str] = []
        with patch("click.echo", side_effect=lambda msg: echo_calls.append(str(msg))):
            with patch("click.prompt", return_value=DebugAction.CONTINUE.value):
                adapter.on_breakpoint(hit)

        # No message line should appear
        assert not any("None" in call for call in echo_calls)

    def test_on_snapshot_stores_snapshot(self) -> None:
        """Line 90: on_snapshot appends to _snapshots list."""
        adapter = InteractiveDebugAdapter()
        snapshot = _make_snapshot()

        adapter.on_snapshot(snapshot)

        assert len(adapter._snapshots) == 1
        assert adapter._snapshots[0] is snapshot

    def test_on_snapshot_with_logger_logs_debug(self) -> None:
        """Lines 90-92: on_snapshot calls logger.debug when logger is configured."""
        logger = _make_logger()
        adapter = InteractiveDebugAdapter(logger=logger)
        snapshot = _make_snapshot(stage="after_silver", records_fetched=50)

        adapter.on_snapshot(snapshot)

        logger.debug.assert_called_once()
        call_args = logger.debug.call_args
        assert call_args[0][0] == "debug_snapshot"
        assert call_args[1]["stage"] == "after_silver"
        assert call_args[1]["records_fetched"] == 50

    def test_on_snapshot_without_logger_does_not_log(self) -> None:
        """Lines 90-92: on_snapshot with no logger just stores snapshot."""
        adapter = InteractiveDebugAdapter(logger=None)
        snapshot = _make_snapshot()

        # Should not raise
        adapter.on_snapshot(snapshot)

        assert len(adapter._snapshots) == 1

    def test_on_snapshot_accumulates_multiple_snapshots(self) -> None:
        """Line 90: multiple snapshots accumulate."""
        adapter = InteractiveDebugAdapter()

        for i in range(5):
            adapter.on_snapshot(_make_snapshot(records_fetched=i))

        assert len(adapter._snapshots) == 5

    def test_init_with_logger(self) -> None:
        """Line 46: logger stored on init."""
        logger = _make_logger()
        adapter = InteractiveDebugAdapter(logger=logger)
        assert adapter._logger is logger


@pytest.mark.unit
class TestLoggingDebugAdapterBoost:
    """Boost tests for LoggingDebugAdapter — covering additional paths."""

    def test_on_breakpoint_logs_all_fields(self) -> None:
        """Verify all snapshot fields are logged."""
        logger = _make_logger()
        adapter = LoggingDebugAdapter(logger=logger)
        snapshot = _make_snapshot(
            records_fetched=100,
            records_bronze=99,
            records_silver=90,
            records_gold=85,
            records_quarantined=5,
        )
        hit = BreakpointHit(
            breakpoint=StageBreakpoint.AFTER_GOLD,
            snapshot=snapshot,
            message="gold done",
        )

        action = adapter.on_breakpoint(hit)

        assert action == DebugAction.CONTINUE
        logger.info.assert_called_once()
        call_kwargs = logger.info.call_args[1]
        assert call_kwargs["records_fetched"] == 100
        assert call_kwargs["records_bronze"] == 99
        assert call_kwargs["records_silver"] == 90
        assert call_kwargs["records_gold"] == 85
        assert call_kwargs["records_quarantined"] == 5
        assert call_kwargs["message"] == "gold done"

    def test_on_breakpoint_no_message(self) -> None:
        """on_breakpoint with None message is forwarded to logger."""
        logger = _make_logger()
        adapter = LoggingDebugAdapter(logger=logger)
        hit = _make_hit(message=None)
        adapter.on_breakpoint(hit)
        call_kwargs = logger.info.call_args[1]
        assert call_kwargs["message"] is None

    def test_on_snapshot_logs_stage_and_fetched(self) -> None:
        """on_snapshot logs stage and records_fetched."""
        logger = _make_logger()
        adapter = LoggingDebugAdapter(logger=logger)
        snapshot = _make_snapshot(stage="pre_silver", records_fetched=77)
        adapter.on_snapshot(snapshot)
        logger.debug.assert_called_once()
        call_kwargs = logger.debug.call_args[1]
        assert call_kwargs["stage"] == "pre_silver"
        assert call_kwargs["records_fetched"] == 77
