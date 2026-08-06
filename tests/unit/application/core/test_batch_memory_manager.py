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
"""Unit tests for BatchMemoryManagerService.

Tests memory budget enforcement, adaptive batch-size adjustment,
GC/recovery after pressure relief, and config-based estimation.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.application.core.batch_memory_manager import BatchMemoryManagerService
from bioetl.domain.config import MemoryConfig


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_monitor(recommended: int = 100) -> MagicMock:
    monitor = MagicMock()
    monitor.get_recommended_batch_size = MagicMock(return_value=recommended)
    return monitor


def _make_config(
    *,
    max_batch_memory_mb: int = 512,
    min_batch_size: int = 10,
    check_interval_records: int = 100,
    enable_adaptive_sizing: bool = True,
) -> MemoryConfig:
    return MemoryConfig(
        max_batch_memory_mb=max_batch_memory_mb,
        min_batch_size=min_batch_size,
        check_interval_records=check_interval_records,
        enable_adaptive_sizing=enable_adaptive_sizing,
    )


# ---------------------------------------------------------------------------
# __init__ / enabled flag
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBatchMemoryManagerInit:
    """Tests for BatchMemoryManagerService initialisation."""

    def test_enabled_when_monitor_provided(self):
        """enabled=True when a memory_monitor is supplied."""
        manager = BatchMemoryManagerService(
            initial_batch_size=500,
            memory_monitor=_make_monitor(),
        )
        assert manager.enabled is True

    def test_enabled_when_memory_config_adaptive(self):
        """enabled=True when config.enable_adaptive_sizing=True."""
        manager = BatchMemoryManagerService(
            initial_batch_size=500,
            memory_config=_make_config(enable_adaptive_sizing=True),
        )
        assert manager.enabled is True

    def test_disabled_when_no_monitor_and_no_config(self):
        """enabled=False when neither monitor nor config supplied."""
        manager = BatchMemoryManagerService(initial_batch_size=500)
        assert manager.enabled is False

    def test_disabled_when_adaptive_sizing_off(self):
        """enabled=False when config has enable_adaptive_sizing=False and no monitor."""
        manager = BatchMemoryManagerService(
            initial_batch_size=500,
            memory_config=_make_config(enable_adaptive_sizing=False),
        )
        assert manager.enabled is False

    def test_initial_min_batch_size_equals_initial_batch_size(self):
        """min_batch_size_used starts at initial_batch_size."""
        manager = BatchMemoryManagerService(initial_batch_size=200)
        assert manager.min_batch_size_used == 200

    def test_initial_reduction_count_is_zero(self):
        """batch_size_reductions starts at 0."""
        manager = BatchMemoryManagerService(initial_batch_size=100)
        assert manager.batch_size_reductions == 0

    def test_monitor_and_adaptive_config_both_enable(self):
        """Monitor takes priority; enabled regardless of config flag."""
        manager = BatchMemoryManagerService(
            initial_batch_size=100,
            memory_monitor=_make_monitor(),
            memory_config=_make_config(enable_adaptive_sizing=False),
        )
        # monitor is present so enabled must be True
        assert manager.enabled is True


# ---------------------------------------------------------------------------
# get_check_interval
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetCheckInterval:
    """Tests for BatchMemoryManagerService.get_check_interval."""

    def test_returns_config_interval_when_config_present(self):
        """Returns check_interval_records from memory_config."""
        manager = BatchMemoryManagerService(
            initial_batch_size=100,
            memory_config=_make_config(check_interval_records=50),
        )
        assert manager.get_check_interval() == 50

    def test_returns_default_100_when_no_config(self):
        """Returns 100 when no memory_config is set."""
        manager = BatchMemoryManagerService(initial_batch_size=100)
        assert manager.get_check_interval() == 100

    def test_returns_default_100_with_monitor_but_no_config(self):
        """Returns 100 when monitor present but no config."""
        manager = BatchMemoryManagerService(
            initial_batch_size=100,
            memory_monitor=_make_monitor(),
        )
        assert manager.get_check_interval() == 100


# ---------------------------------------------------------------------------
# check_pressure
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCheckPressure:
    """Tests for BatchMemoryManagerService.check_pressure."""

    def test_returns_current_size_when_disabled(self):
        """Returns current_size unchanged when adaptive sizing is disabled."""
        manager = BatchMemoryManagerService(initial_batch_size=500)
        result = manager.check_pressure(
            current_size=500, check_interval=100, records_fetched=100
        )
        assert result == 500

    def test_returns_current_size_before_interval(self):
        """Returns current_size when records_fetched % interval != 0."""
        manager = BatchMemoryManagerService(
            initial_batch_size=500,
            memory_monitor=_make_monitor(recommended=200),
        )
        result = manager.check_pressure(
            current_size=500, check_interval=100, records_fetched=50
        )
        assert result == 500

    def test_calls_adjust_at_interval_boundary(self):
        """Calls _adjust when records_fetched % check_interval == 0."""
        monitor = _make_monitor(recommended=300)
        manager = BatchMemoryManagerService(
            initial_batch_size=500,
            memory_monitor=monitor,
        )
        result = manager.check_pressure(
            current_size=500, check_interval=100, records_fetched=100
        )
        monitor.get_recommended_batch_size.assert_called_once_with(500)
        assert result == 300

    def test_reduces_batch_size_under_pressure(self):
        """Returns smaller batch size when monitor recommends reduction."""
        monitor = _make_monitor(recommended=50)
        manager = BatchMemoryManagerService(
            initial_batch_size=500,
            memory_monitor=monitor,
        )
        result = manager.check_pressure(
            current_size=500, check_interval=100, records_fetched=100
        )
        assert result == 50
        assert manager.batch_size_reductions == 1

    def test_tracks_min_batch_size_used(self):
        """min_batch_size_used is updated when size is reduced."""
        monitor = _make_monitor(recommended=25)
        manager = BatchMemoryManagerService(
            initial_batch_size=500,
            memory_monitor=monitor,
        )
        manager.check_pressure(
            current_size=500, check_interval=100, records_fetched=100
        )
        assert manager.min_batch_size_used == 25

    def test_logs_size_reduction(self):
        """Logger.info is called when batch size is reduced."""
        monitor = _make_monitor(recommended=10)
        mock_logger = MagicMock()
        manager = BatchMemoryManagerService(
            initial_batch_size=500,
            memory_monitor=monitor,
            logger=mock_logger,
        )
        manager.check_pressure(
            current_size=500, check_interval=100, records_fetched=100
        )
        mock_logger.info.assert_called_once()

    def test_does_not_log_when_no_reduction(self):
        """Logger.info is NOT called when batch size is not reduced."""
        monitor = _make_monitor(recommended=500)  # Same size — no reduction
        mock_logger = MagicMock()
        manager = BatchMemoryManagerService(
            initial_batch_size=500,
            memory_monitor=monitor,
            logger=mock_logger,
        )
        manager.check_pressure(
            current_size=500, check_interval=100, records_fetched=100
        )
        mock_logger.info.assert_not_called()

    def test_accumulates_reduction_count_across_calls(self):
        """batch_size_reductions increments on each pressure event."""
        monitor = MagicMock()
        monitor.get_recommended_batch_size.side_effect = [400, 300, 200]
        manager = BatchMemoryManagerService(
            initial_batch_size=500,
            memory_monitor=monitor,
        )
        for fetched in [100, 200, 300]:
            manager.check_pressure(
                current_size=500, check_interval=100, records_fetched=fetched
            )

        assert manager.batch_size_reductions == 3

    def test_records_pressure_decision_trace(self):
        """Pressure decisions are retained as replay-visible trace entries."""
        monitor = _make_monitor(recommended=250)
        manager = BatchMemoryManagerService(
            initial_batch_size=500,
            memory_monitor=monitor,
            memory_config=_make_config(check_interval_records=100),
        )

        result = manager.check_pressure(
            current_size=500,
            check_interval=100,
            records_fetched=100,
        )

        assert result == 250
        trace = manager.decision_trace_dicts()
        assert trace == (
            {
                "decision_index": 1,
                "record_index": 100,
                "stage": "pressure_check",
                "old_batch_size": 500,
                "new_batch_size": 250,
                "adaptive_sizing_enabled": True,
                "monitor_available": True,
                "config_available": True,
                "pressure_state": None,
                "monitor_mode": "unknown",
                "reason": "monitor_recommended_reduction",
            },
        )

    def test_emits_bounded_memory_metrics_for_pressure_resize(self):
        """Pressure and resize decisions emit low-cardinality metrics."""
        metrics = MagicMock()
        manager = BatchMemoryManagerService(
            initial_batch_size=500,
            memory_config=_make_config(max_batch_memory_mb=1, min_batch_size=50),
            metrics=metrics,
            pipeline_name="chembl_activity",
        )

        manager.check_pressure(
            current_size=2000,
            check_interval=100,
            records_fetched=100,
        )

        expected_labels = {
            "pipeline": "chembl_activity",
            "stage": "pressure_check",
            "reason": "config_budget_exceeded",
            "monitor_mode": "config_budget",
            "status": "reduced",
        }
        metrics.set_gauge.assert_called_once_with(
            "bioetl_memory_pressure_state",
            1.0,
            expected_labels,
        )
        metrics.increment_counter.assert_any_call(
            "bioetl_memory_pressure_events_total",
            1,
            expected_labels,
        )
        metrics.increment_counter.assert_any_call(
            "bioetl_memory_batch_resize_events_total",
            1,
            expected_labels,
        )

    def test_fallback_monitor_mode_metric_is_bounded(self):
        """Fallback monitor modes are emitted without host-specific labels."""
        metrics = MagicMock()
        monitor = _make_monitor(recommended=250)
        monitor.get_monitor_mode.return_value = "estimate"
        monitor.get_last_pressure_state.return_value = True
        manager = BatchMemoryManagerService(
            initial_batch_size=500,
            memory_monitor=monitor,
            metrics=metrics,
            pipeline_name="chembl_activity",
        )

        manager.check_pressure(
            current_size=500,
            check_interval=100,
            records_fetched=100,
        )

        fallback_call = next(
            call
            for call in metrics.increment_counter.call_args_list
            if call.args[0] == "bioetl_memory_monitor_fallback_events_total"
        )
        assert fallback_call.args[2] == {
            "pipeline": "chembl_activity",
            "stage": "pressure_check",
            "reason": "monitor_recommended_reduction",
            "monitor_mode": "estimate",
            "status": "reduced",
        }


# ---------------------------------------------------------------------------
# maybe_recover
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMaybeRecover:
    """Tests for BatchMemoryManagerService.maybe_recover."""

    def test_manager_maybe_recover__size_when_disabled__a14b9654(self):
        """Returns current_size unchanged when adaptive sizing is disabled."""
        manager = BatchMemoryManagerService(initial_batch_size=500)
        result = manager.maybe_recover(current_size=100)
        assert result == 100

    def test_delegates_to_monitor_when_present(self):
        """Uses monitor.get_recommended_batch_size for recovery."""
        monitor = _make_monitor(recommended=150)
        manager = BatchMemoryManagerService(
            initial_batch_size=500,
            memory_monitor=monitor,
        )
        result = manager.maybe_recover(current_size=100)
        monitor.get_recommended_batch_size.assert_called_once_with(100)
        assert result == 150

    def test_recovers_toward_initial_size_without_monitor(self):
        """Without monitor, batch size grows toward initial_batch_size at 10%/step."""
        manager = BatchMemoryManagerService(
            initial_batch_size=500,
            memory_config=_make_config(enable_adaptive_sizing=True),
        )
        result = manager.maybe_recover(current_size=100)
        # 10% growth: int(100 * 1.1) = 110
        assert result == 110

    def test_tiny_size_recovery_always_advances_by_at_least_one(self) -> None:
        """Integer 10% growth must not stall at size 1 (int(1.1)==1)."""
        manager = BatchMemoryManagerService(
            initial_batch_size=10,
            memory_config=_make_config(enable_adaptive_sizing=True),
        )
        assert manager.maybe_recover(current_size=1) == 2
        assert manager.maybe_recover(current_size=2) == 3

    def test_does_not_exceed_initial_size_on_recovery(self):
        """Recovery never overshoots initial_batch_size."""
        manager = BatchMemoryManagerService(
            initial_batch_size=500,
            memory_config=_make_config(enable_adaptive_sizing=True),
        )
        result = manager.maybe_recover(current_size=490)
        assert result == 500

    def test_no_change_when_already_at_initial_size(self):
        """Returns current_size unchanged when already at initial_batch_size."""
        manager = BatchMemoryManagerService(
            initial_batch_size=500,
            memory_config=_make_config(enable_adaptive_sizing=True),
        )
        result = manager.maybe_recover(current_size=500)
        assert result == 500

    def test_records_recovery_decision_without_overshooting_initial_size(self):
        """Recovery trace captures bounded relief decisions."""
        manager = BatchMemoryManagerService(
            initial_batch_size=500,
            memory_config=_make_config(enable_adaptive_sizing=True),
        )

        result = manager.maybe_recover(current_size=490)

        assert result == 500
        assert manager.decision_trace_dicts()[-1]["reason"] == (
            "config_recovery_toward_initial"
        )
        assert manager.decision_trace_dicts()[-1]["new_batch_size"] == 500

    def test_repeated_config_recovery_stabilizes_at_initial_size(self) -> None:
        """Config-driven recovery should converge monotonically to the initial size."""
        manager = BatchMemoryManagerService(
            initial_batch_size=500,
            memory_config=_make_config(enable_adaptive_sizing=True),
        )

        current_size = 100
        observed_sizes: list[int] = []
        for _ in range(20):
            current_size = manager.maybe_recover(current_size=current_size)
            observed_sizes.append(current_size)

        assert observed_sizes == sorted(observed_sizes)
        assert all(size <= 500 for size in observed_sizes)
        assert observed_sizes[-1] == 500

    def test_decision_trace_is_bounded_after_many_recovery_steps(self) -> None:
        """Replay-visible decision trace must stay bounded during long runs."""
        manager = BatchMemoryManagerService(
            initial_batch_size=500,
            memory_config=_make_config(enable_adaptive_sizing=True),
        )

        current_size = 10
        for _ in range(160):
            current_size = manager.maybe_recover(current_size=current_size)

        trace = manager.decision_trace_dicts()
        assert len(trace) == manager._MAX_DECISION_TRACE_ENTRIES
        assert trace[0]["decision_index"] == 33
        assert trace[-1]["decision_index"] == 160


# ---------------------------------------------------------------------------
# _estimate_from_config
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEstimateFromConfig:
    """Tests for BatchMemoryManagerService._estimate_from_config."""

    def test_returns_current_size_when_no_config(self):
        """Returns current_size when no memory_config set."""
        manager = BatchMemoryManagerService(initial_batch_size=100)
        result = manager._estimate_from_config(100)
        assert result == 100

    def test_caps_at_max_batch_memory_limit(self):
        """Returns max_records limit when current_size exceeds budget."""
        # max_batch_memory_mb=10 -> max_records = 10 * 1000 = 10000
        manager = BatchMemoryManagerService(
            initial_batch_size=20000,
            memory_config=_make_config(max_batch_memory_mb=10, min_batch_size=5),
        )
        result = manager._estimate_from_config(20000)
        assert result == 10000

    def test_respects_min_batch_size_floor(self):
        """Returns at least min_batch_size even when memory budget is very small."""
        manager = BatchMemoryManagerService(
            initial_batch_size=20000,
            memory_config=_make_config(
                max_batch_memory_mb=1,  # 1 * 1000 = 1000 records budget
                min_batch_size=5000,
            ),
        )
        result = manager._estimate_from_config(20000)
        assert result == 5000

    def test_returns_current_size_when_within_budget(self):
        """Returns current_size unchanged when it fits within memory budget."""
        # max_batch_memory_mb=512 -> 512000 records
        manager = BatchMemoryManagerService(
            initial_batch_size=1000,
            memory_config=_make_config(max_batch_memory_mb=512),
        )
        result = manager._estimate_from_config(1000)
        assert result == 1000

    def test_boundary_exactly_at_max_records(self):
        """Returns current_size when it exactly equals max_records."""
        manager = BatchMemoryManagerService(
            initial_batch_size=10000,
            memory_config=_make_config(max_batch_memory_mb=10, min_batch_size=5),
        )
        # 10 * 1000 = 10000 exactly
        result = manager._estimate_from_config(10000)
        assert result == 10000
