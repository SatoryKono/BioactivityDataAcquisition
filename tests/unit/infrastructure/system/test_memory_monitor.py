"""Unit tests for MemoryMonitor infrastructure component.

Tests cover: adaptive batch sizing, memory pressure detection,
psutil fallback, estimate path, and batch calculation utilities.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, mock_open, patch

import pytest

from bioetl.domain.config import MemoryConfig
from bioetl.domain.ports import MemoryStats
from bioetl.infrastructure.system.memory_monitor import (
    MemoryMonitor,
    _check_psutil_available,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_monitor(
    *,
    threshold: float = 0.8,
    adaptive: bool = True,
    min_batch: int = 10,
    max_batch_memory_mb: int = 512,
    logger: MagicMock | None = None,
) -> MemoryMonitor:
    config = MemoryConfig(
        memory_pressure_threshold=threshold,
        enable_adaptive_sizing=adaptive,
        min_batch_size=min_batch,
        max_batch_memory_mb=max_batch_memory_mb,
    )
    return MemoryMonitor(config=config, logger=logger)


def _mock_stats(percent_used: float = 0.5) -> MemoryStats:
    """Create a MemoryStats with given percent_used."""
    return MemoryStats(
        used_mb=4096.0 * percent_used,
        available_mb=4096.0 * (1 - percent_used),
        total_mb=4096.0,
        percent_used=percent_used,
        process_mb=256.0,
    )


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCheckPsutilAvailable:
    """Tests for module-level _check_psutil_available helper."""

    def test_returns_bool(self) -> None:
        """Function returns a boolean."""
        result = _check_psutil_available()
        assert isinstance(result, bool)

    def test_caches_result(self) -> None:
        """Calling twice returns the same value (cache hit)."""
        first = _check_psutil_available()
        second = _check_psutil_available()
        assert first == second


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMemoryMonitorInit:
    """Tests for MemoryMonitor initialization."""

    def test_init_no_logger(self) -> None:
        """Monitor initialises without a logger."""
        monitor = _make_monitor()
        assert monitor.config.enable_adaptive_sizing is True

    def test_init_with_logger_when_psutil_available(self) -> None:
        """Logger.debug is called when psutil is available."""
        logger = MagicMock()
        with patch(
            "bioetl.infrastructure.system.memory_monitor._check_psutil_available",
            return_value=True,
        ):
            monitor = MemoryMonitor(config=MemoryConfig(), logger=logger)
        assert monitor._psutil_available is True
        logger.debug.assert_called_once()

    def test_init_with_logger_when_psutil_unavailable(self) -> None:
        """Logger.debug is called when psutil is NOT available."""
        logger = MagicMock()
        with patch(
            "bioetl.infrastructure.system.memory_monitor._check_psutil_available",
            return_value=False,
        ):
            monitor = MemoryMonitor(config=MemoryConfig(), logger=logger)
        assert monitor._psutil_available is False
        logger.debug.assert_called_once()


# ---------------------------------------------------------------------------
# get_memory_stats — estimate path (always available, no OS deps)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetMemoryStatsEstimate:
    """Tests for _get_stats_estimate (conservative fallback)."""

    def test_estimate_returns_valid_stats(self) -> None:
        """Estimate path returns a valid MemoryStats."""
        monitor = _make_monitor()
        stats = monitor._get_stats_estimate()
        assert isinstance(stats, MemoryStats)
        assert stats.total_mb == pytest.approx(8192.0)
        assert stats.available_mb == pytest.approx(4096.0)
        assert stats.percent_used == pytest.approx(0.5)
        assert stats.process_mb == pytest.approx(256.0)
        assert monitor.get_monitor_mode() == "estimate"

    def test_fallback_calls_estimate_on_win32(self) -> None:
        """On win32 platform _get_stats_fallback calls estimate."""
        monitor = _make_monitor()
        with patch("sys.platform", "win32"):
            stats = monitor._get_stats_fallback()
        assert isinstance(stats, MemoryStats)
        assert stats.total_mb == pytest.approx(8192.0)


# ---------------------------------------------------------------------------
# get_memory_stats — psutil path (mocked)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetMemoryStatsPsutil:
    """Tests for _get_stats_psutil with mocked psutil."""

    def _make_psutil_mock(self, percent: float = 60.0) -> MagicMock:
        psutil_mock = MagicMock()
        vm = MagicMock()
        vm.used = 6 * 1024 * 1024 * 1024  # 6 GB in bytes
        vm.available = 4 * 1024 * 1024 * 1024  # 4 GB
        vm.total = 10 * 1024 * 1024 * 1024  # 10 GB
        vm.percent = percent
        psutil_mock.virtual_memory.return_value = vm
        process_mock = MagicMock()
        mem_info = MagicMock()
        mem_info.rss = 256 * 1024 * 1024  # 256 MB
        process_mock.memory_info.return_value = mem_info
        psutil_mock.Process.return_value = process_mock
        return psutil_mock

    def test_get_stats_psutil_returns_stats(self) -> None:
        """Psutil path returns populated MemoryStats."""
        psutil_mock = self._make_psutil_mock(percent=60.0)
        monitor = _make_monitor()
        monitor._psutil_available = True

        with patch(
            "bioetl.infrastructure.system.memory_monitor._PSUTIL_MODULE", psutil_mock
        ):
            stats = monitor._get_stats_psutil()

        assert isinstance(stats, MemoryStats)
        assert stats.percent_used == pytest.approx(0.6)  # 60 / 100
        assert stats.process_mb == pytest.approx(256.0)

    def test_get_stats_psutil_caches_process(self) -> None:
        """Process instance is cached across calls."""
        psutil_mock = self._make_psutil_mock()
        monitor = _make_monitor()
        monitor._psutil_available = True

        with patch(
            "bioetl.infrastructure.system.memory_monitor._PSUTIL_MODULE", psutil_mock
        ):
            monitor._get_stats_psutil()
            monitor._get_stats_psutil()

        # Process() should be called once (cached after first call)
        assert psutil_mock.Process.call_count == 1


# ---------------------------------------------------------------------------
# is_under_pressure
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsUnderPressure:
    """Tests for MemoryMonitor.is_under_pressure()."""

    def test_no_pressure_when_adaptive_disabled(self) -> None:
        """is_under_pressure returns False when adaptive sizing is disabled."""
        monitor = _make_monitor(adaptive=False)
        assert monitor.is_under_pressure() is False

    def test_pressure_detected_above_threshold(self) -> None:
        """is_under_pressure returns True above threshold."""
        monitor = _make_monitor(threshold=0.7)
        with patch.object(monitor, "get_memory_stats", return_value=_mock_stats(0.9)):
            assert monitor.is_under_pressure() is True

    def test_no_pressure_below_threshold(self) -> None:
        """is_under_pressure returns False below threshold."""
        monitor = _make_monitor(threshold=0.8)
        with patch.object(monitor, "get_memory_stats", return_value=_mock_stats(0.5)):
            assert monitor.is_under_pressure() is False

    def test_pressure_at_exact_threshold(self) -> None:
        """is_under_pressure returns False at exactly threshold (uses >=)."""
        monitor = _make_monitor(threshold=0.8)
        with patch.object(monitor, "get_memory_stats", return_value=_mock_stats(0.8)):
            assert monitor.is_under_pressure() is True
        assert monitor.get_last_pressure_state() is True

    def test_monitor_mode_and_pressure_state_are_bounded(self) -> None:
        """Adaptive decisions expose replay-safe monitor mode and pressure state."""
        monitor = _make_monitor(threshold=0.8)
        with patch.object(monitor, "get_memory_stats", return_value=_mock_stats(0.3)):
            result = monitor.get_recommended_batch_size(500)

        assert result == 500
        assert monitor.get_last_pressure_state() is False
        assert monitor.get_monitor_mode() == "unknown"


# ---------------------------------------------------------------------------
# get_recommended_batch_size
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetRecommendedBatchSize:
    """Tests for MemoryMonitor.get_recommended_batch_size()."""

    def test_returns_current_size_when_adaptive_disabled(self) -> None:
        """Returns current_batch_size unchanged when adaptive sizing is off."""
        monitor = _make_monitor(adaptive=False)
        result = monitor.get_recommended_batch_size(500)
        assert result == 500

    def test_reduces_batch_size_under_pressure(self) -> None:
        """Batch size is reduced when memory is under pressure."""
        monitor = _make_monitor(threshold=0.7, min_batch=10)
        with patch.object(monitor, "get_memory_stats", return_value=_mock_stats(0.9)):
            result = monitor.get_recommended_batch_size(1000)
        # Standard reduction: 50% -> 500
        assert result == 500

    def test_respects_min_batch_size(self) -> None:
        """Batch size never goes below min_batch_size."""
        monitor = _make_monitor(threshold=0.7, min_batch=100)
        with patch.object(monitor, "get_memory_stats", return_value=_mock_stats(0.9)):
            result = monitor.get_recommended_batch_size(10)
        assert result == 100

    def test_no_reduction_without_pressure(self) -> None:
        """Batch size is not reduced when no pressure."""
        monitor = _make_monitor(threshold=0.8)
        with patch.object(monitor, "get_memory_stats", return_value=_mock_stats(0.5)):
            result = monitor.get_recommended_batch_size(500)
        assert result == 500

    def test_gradual_recovery_when_pressure_relieved(self) -> None:
        """Batch size recovers gradually when pressure is relieved."""
        monitor = _make_monitor(threshold=0.8)
        monitor._last_batch_size = 1000  # Previously was 1000

        with patch.object(monitor, "get_memory_stats", return_value=_mock_stats(0.3)):
            result = monitor.get_recommended_batch_size(400)  # Currently reduced to 400

        # Recovery: 25% increase toward 1000
        assert result == min(int(400 * 1.25), 1000)
        assert result == 500

    def test_recovery_uses_pre_pressure_batch_size_as_target(self) -> None:
        """Recovery is anchored to the size that was active before pressure."""
        monitor = _make_monitor(threshold=0.8)

        with patch.object(monitor, "get_memory_stats") as mock_stats:
            mock_stats.return_value = _mock_stats(0.9)
            reduced = monitor.get_recommended_batch_size(1000)

            assert reduced == 500
            assert monitor._recovery_target_batch_size == 1000

            mock_stats.return_value = _mock_stats(0.3)
            recovered_once = monitor.get_recommended_batch_size(reduced)
            recovered_twice = monitor.get_recommended_batch_size(recovered_once)

        assert recovered_once == 625
        assert recovered_twice == 781
        assert monitor._last_batch_size == 1000

    def test_recovery_clears_target_after_full_restore(self) -> None:
        """Recovery target is cleared once the original size is restored."""
        monitor = _make_monitor(threshold=0.8)

        with patch.object(monitor, "get_memory_stats") as mock_stats:
            mock_stats.return_value = _mock_stats(0.9)
            current_size = monitor.get_recommended_batch_size(1000)

            mock_stats.return_value = _mock_stats(0.3)
            for _ in range(8):
                current_size = monitor.get_recommended_batch_size(current_size)

        assert current_size == 1000
        assert monitor._recovery_target_batch_size is None

    def test_logs_warning_on_reduction(self) -> None:
        """Logger.warning is called when batch is reduced."""
        logger = MagicMock()
        monitor = _make_monitor(threshold=0.7, min_batch=10, logger=logger)
        with patch.object(monitor, "get_memory_stats", return_value=_mock_stats(0.9)):
            monitor.get_recommended_batch_size(1000)
        logger.warning.assert_called_once()

    def test_resets_pressure_count_on_relief(self) -> None:
        """Consecutive pressure count resets when pressure is relieved."""
        monitor = _make_monitor(threshold=0.8)
        monitor._consecutive_pressure_count = 5

        with patch.object(monitor, "get_memory_stats", return_value=_mock_stats(0.3)):
            monitor.get_recommended_batch_size(500)

        assert monitor._consecutive_pressure_count == 0

    @pytest.mark.parametrize("initial_size", [1, 2, 5, 10, 25, 100])
    def test_repeated_pressure_never_drops_below_min_batch_size(
        self, initial_size: int
    ) -> None:
        """Sustained pressure must stay monotonic but never reach zero/negative sizes."""
        monitor = _make_monitor(threshold=0.8, min_batch=10)
        current_size = initial_size

        with patch.object(monitor, "get_memory_stats", return_value=_mock_stats(0.95)):
            observed_sizes = []
            for _ in range(8):
                current_size = monitor.get_recommended_batch_size(current_size)
                observed_sizes.append(current_size)

        assert all(size >= 10 for size in observed_sizes)
        assert all(size > 0 for size in observed_sizes)
        assert observed_sizes == sorted(observed_sizes, reverse=True)

    @pytest.mark.parametrize("relief_steps", [1, 2, 4, 8, 12])
    def test_repeated_relief_stabilizes_at_recovery_target(
        self, relief_steps: int
    ) -> None:
        """Repeated relief calls recover monotonically and eventually stabilize."""
        monitor = _make_monitor(threshold=0.8)

        with patch.object(monitor, "get_memory_stats") as mock_stats:
            mock_stats.return_value = _mock_stats(0.9)
            current_size = monitor.get_recommended_batch_size(1000)

            mock_stats.return_value = _mock_stats(0.2)
            observed_sizes = []
            for _ in range(relief_steps):
                current_size = monitor.get_recommended_batch_size(current_size)
                observed_sizes.append(current_size)

        assert all(size <= 1000 for size in observed_sizes)
        assert observed_sizes == sorted(observed_sizes)
        if relief_steps >= 8:
            assert observed_sizes[-1] == 1000
            assert monitor._recovery_target_batch_size is None
        else:
            assert observed_sizes[-1] <= 1000


# ---------------------------------------------------------------------------
# _get_reduction_factor
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetReductionFactor:
    """Tests for pressure-duration-aware reduction factors."""

    def test_standard_reduction_at_1_press(self) -> None:
        """Standard 50% reduction for initial pressure."""
        monitor = _make_monitor()
        monitor._consecutive_pressure_count = 1
        assert monitor._get_reduction_factor() == pytest.approx(0.5)

    def test_moderate_reduction_at_3_press(self) -> None:
        """Moderate-aggressive 35% reduction at 3 consecutive."""
        monitor = _make_monitor()
        monitor._consecutive_pressure_count = 3
        assert monitor._get_reduction_factor() == pytest.approx(0.35)

    def test_aggressive_reduction_at_5_press(self) -> None:
        """Aggressive 25% reduction at 5+ consecutive."""
        monitor = _make_monitor()
        monitor._consecutive_pressure_count = 5
        assert monitor._get_reduction_factor() == pytest.approx(0.25)

    def test_aggressive_reduction_at_10_press(self) -> None:
        """Aggressive 25% reduction beyond 5 consecutive."""
        monitor = _make_monitor()
        monitor._consecutive_pressure_count = 10
        assert monitor._get_reduction_factor() == pytest.approx(0.25)


# ---------------------------------------------------------------------------
# estimate_batch_memory_mb
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEstimateBatchMemoryMb:
    """Tests for estimate_batch_memory_mb()."""

    def test_estimate_is_positive(self) -> None:
        """Estimate returns positive value."""
        monitor = _make_monitor()
        result = monitor.estimate_batch_memory_mb(1000)
        assert result > 0

    def test_estimate_scales_with_record_count(self) -> None:
        """Estimate scales linearly with record_count."""
        monitor = _make_monitor()
        est_100 = monitor.estimate_batch_memory_mb(100)
        est_200 = monitor.estimate_batch_memory_mb(200)
        assert est_200 / est_100 == pytest.approx(2.0, abs=0.001)

    def test_estimate_scales_with_record_size(self) -> None:
        """Estimate scales with avg_record_size_bytes."""
        monitor = _make_monitor()
        est_1k = monitor.estimate_batch_memory_mb(100, avg_record_size_bytes=1024)
        est_2k = monitor.estimate_batch_memory_mb(100, avg_record_size_bytes=2048)
        assert est_2k / est_1k == pytest.approx(2.0, abs=0.001)

    def test_estimate_uses_overhead_factor(self) -> None:
        """Estimate applies 2.5x overhead factor."""
        monitor = _make_monitor()
        expected = (100 * 1024 * 2.5) / (1024 * 1024)
        result = monitor.estimate_batch_memory_mb(100, avg_record_size_bytes=1024)
        assert result == pytest.approx(expected, abs=0.001)


# ---------------------------------------------------------------------------
# calculate_max_batch_size
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCalculateMaxBatchSize:
    """Tests for calculate_max_batch_size()."""

    def test_returns_positive_integer(self) -> None:
        """Returns a positive integer."""
        monitor = _make_monitor(max_batch_memory_mb=512)
        result = monitor.calculate_max_batch_size()
        assert isinstance(result, int)
        assert result > 0

    def test_smaller_record_means_larger_batch(self) -> None:
        """Smaller records allow larger batches."""
        monitor = _make_monitor(max_batch_memory_mb=512)
        batch_small = monitor.calculate_max_batch_size(avg_record_size_bytes=512)
        batch_large = monitor.calculate_max_batch_size(avg_record_size_bytes=4096)
        assert batch_small > batch_large

    def test_respects_min_batch_size(self) -> None:
        """Result is never below min_batch_size."""
        monitor = _make_monitor(max_batch_memory_mb=1, min_batch=10)
        # Very large record size → calculated batch could be < min
        result = monitor.calculate_max_batch_size(
            avg_record_size_bytes=10 * 1024 * 1024
        )
        assert result >= 10


# ---------------------------------------------------------------------------
# get_memory_stats dispatch
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetMemoryStatsDispatch:
    """Tests for get_memory_stats() dispatch logic."""

    def test_uses_psutil_when_available(self) -> None:
        """get_memory_stats calls _get_stats_psutil when available."""
        monitor = _make_monitor()
        monitor._psutil_available = True
        with patch.object(
            monitor, "_get_stats_psutil", return_value=_mock_stats(0.3)
        ) as mock_psutil:
            monitor.get_memory_stats()
        mock_psutil.assert_called_once()

    def test_uses_fallback_when_psutil_unavailable(self) -> None:
        """get_memory_stats calls _get_stats_fallback when unavailable."""
        monitor = _make_monitor()
        monitor._psutil_available = False
        with patch.object(
            monitor, "_get_stats_fallback", return_value=_mock_stats(0.5)
        ) as mock_fallback:
            monitor.get_memory_stats()
        mock_fallback.assert_called_once()


@pytest.mark.unit
class TestFallbackResourcePath:
    """Tests for Unix resource fallback branch coverage."""

    def test_fallback_uses_resource_on_non_windows(self) -> None:
        """Non-win32 platform dispatches to _get_stats_resource()."""
        monitor = _make_monitor()
        with (
            patch("sys.platform", "linux"),
            patch.object(
                monitor, "_get_stats_resource", return_value=_mock_stats(0.2)
            ) as mock_resource,
        ):
            stats = monitor._get_stats_fallback()

        assert stats.percent_used == pytest.approx(0.2)
        mock_resource.assert_called_once()

    def test_resource_reads_proc_meminfo(self) -> None:
        """_get_stats_resource parses /proc/meminfo when available."""
        monitor = _make_monitor()
        fake_resource = SimpleNamespace(
            RUSAGE_SELF=0,
            getrusage=lambda _x: SimpleNamespace(ru_maxrss=1024 * 512),  # 512 MB
        )
        meminfo_text = "MemTotal: 8192000 kB\nMemAvailable: 4096000 kB\n"

        with (
            patch.dict("sys.modules", {"resource": fake_resource}),
            patch("pathlib.Path.open", mock_open(read_data=meminfo_text)),
        ):
            stats = monitor._get_stats_resource()

        assert stats.total_mb == pytest.approx(8000.0)
        assert stats.available_mb == pytest.approx(4000.0)
        assert stats.used_mb == pytest.approx(4000.0)
        assert stats.percent_used == pytest.approx(0.5)
        assert stats.process_mb == pytest.approx(512.0)

    def test_resource_falls_back_to_estimate_on_oserror(self) -> None:
        """_get_stats_resource falls back to estimate when /proc access fails."""
        monitor = _make_monitor()
        fake_resource = SimpleNamespace(
            RUSAGE_SELF=0,
            getrusage=lambda _x: SimpleNamespace(ru_maxrss=1024 * 256),
        )

        with (
            patch.dict("sys.modules", {"resource": fake_resource}),
            patch("pathlib.Path.open", side_effect=OSError("no meminfo")),
        ):
            stats = monitor._get_stats_resource()

        assert stats.total_mb == pytest.approx(8192.0)
        assert stats.percent_used == pytest.approx(0.5)

    def test_windows_estimate_mode_is_used_when_psutil_unavailable(self) -> None:
        """Windows fallback documents unavailable-monitoring semantics via estimate mode."""
        monitor = _make_monitor()
        monitor._psutil_available = False

        with patch("sys.platform", "win32"):
            stats = monitor.get_memory_stats()

        assert stats.total_mb == pytest.approx(8192.0)
        assert monitor.get_monitor_mode() == "estimate"

    def test_unix_proc_failure_still_keeps_monitor_mode_bounded(self) -> None:
        """Unavailable `/proc` data must degrade to the bounded estimate mode."""
        monitor = _make_monitor()
        fake_resource = SimpleNamespace(
            RUSAGE_SELF=0,
            getrusage=lambda _x: SimpleNamespace(ru_maxrss=1024 * 128),
        )

        with (
            patch.dict("sys.modules", {"resource": fake_resource}),
            patch("pathlib.Path.open", side_effect=OSError("missing /proc/meminfo")),
        ):
            monitor._get_stats_resource()

        assert monitor.get_monitor_mode() == "estimate"


@pytest.mark.unit
class TestRecoveryLogging:
    """Tests for recovery logging branch in get_recommended_batch_size()."""

    def test_logs_debug_when_pressure_relieved_and_recovering(self) -> None:
        """Logger.debug is emitted when batch size increases in recovery path."""
        logger = MagicMock()
        monitor = _make_monitor(threshold=0.8, logger=logger)
        monitor._last_batch_size = 1000

        with patch.object(monitor, "get_memory_stats", return_value=_mock_stats(0.2)):
            result = monitor.get_recommended_batch_size(400)

        assert result == 500
        logger.debug.assert_any_call(
            "Memory pressure relieved, increasing batch size",
            current_batch_size=400,
            new_batch_size=500,
            memory_percent_used=20.0,
        )
