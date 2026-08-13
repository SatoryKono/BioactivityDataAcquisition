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
"""Unit tests for MemoryMonitor."""

from __future__ import annotations

from io import StringIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.domain.config import MemoryConfig
from bioetl.domain.ports import MemoryStats
import bioetl.infrastructure.system.memory_monitor as memory_monitor_module
from bioetl.infrastructure.system.memory_monitor import MemoryMonitor


@pytest.mark.unit
class TestMemoryConfig:
    """Tests for MemoryConfig dataclass."""

    def test_memory_config_default_values(self) -> None:
        """Test default configuration values."""
        config = MemoryConfig()

        assert config.max_batch_memory_mb == 512
        assert config.memory_pressure_threshold == pytest.approx(0.8)
        assert config.min_batch_size == 10
        assert config.check_interval_records == 100
        assert config.enable_adaptive_sizing is True

    def test_memory_config_accepts_custom_values(self) -> None:
        """Test custom configuration values."""
        config = MemoryConfig(
            max_batch_memory_mb=1024,
            memory_pressure_threshold=0.9,
            min_batch_size=5,
            check_interval_records=50,
            enable_adaptive_sizing=False,
        )

        assert config.max_batch_memory_mb == 1024
        assert config.memory_pressure_threshold == pytest.approx(0.9)
        assert config.min_batch_size == 5
        assert config.check_interval_records == 50
        assert config.enable_adaptive_sizing is False


@pytest.mark.unit
class TestMemoryStats:
    """Tests for MemoryStats dataclass."""

    def test_is_under_pressure_high_usage(self) -> None:
        """Test that high memory usage is detected as pressure."""
        stats = MemoryStats(
            used_mb=7000.0,
            available_mb=1000.0,
            total_mb=8000.0,
            percent_used=0.875,
            process_mb=500.0,
        )

        assert stats.is_under_pressure is True

    def test_is_under_pressure_low_usage(self) -> None:
        """Test that low memory usage is not pressure."""
        stats = MemoryStats(
            used_mb=4000.0,
            available_mb=4000.0,
            total_mb=8000.0,
            percent_used=0.5,
            process_mb=500.0,
        )

        assert stats.is_under_pressure is False

    def test_is_under_pressure_boundary(self) -> None:
        """The coarse helper treats usage equal to 80% as pressure."""
        stats_exactly_80 = MemoryStats(
            used_mb=6400.0,
            available_mb=1600.0,
            total_mb=8000.0,
            percent_used=0.8,
            process_mb=500.0,
        )

        assert stats_exactly_80.is_under_pressure is True

        stats_over_80 = MemoryStats(
            used_mb=6401.0,
            available_mb=1599.0,
            total_mb=8000.0,
            percent_used=0.801,
            process_mb=500.0,
        )

        assert stats_over_80.is_under_pressure is True

    def test_is_under_pressure_at_uses_configured_threshold(self) -> None:
        """Policy-aware pressure checks use caller-provided thresholds."""
        stats = MemoryStats(
            used_mb=6400.0,
            available_mb=1600.0,
            total_mb=8000.0,
            percent_used=0.8,
            process_mb=500.0,
        )

        assert stats.is_under_pressure_at(0.9) is False
        assert stats.is_under_pressure_at(0.8) is True


@pytest.mark.unit
class TestMemoryMonitor:
    """Tests for MemoryMonitor class."""

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        return MagicMock()

    @pytest.fixture
    def monitor(self, mock_logger):
        """Create MemoryMonitor with default config."""
        config = MemoryConfig()
        return MemoryMonitor(config=config, logger=mock_logger)

    def test_get_memory_stats_fallback(self, monitor):
        """Test fallback memory stats when psutil unavailable."""
        with patch.object(monitor, "_psutil_available", False):
            with patch.object(monitor, "_get_stats_fallback") as mock_fallback:
                mock_fallback.return_value = MemoryStats(
                    used_mb=4096.0,
                    available_mb=4096.0,
                    total_mb=8192.0,
                    percent_used=0.5,
                    process_mb=256.0,
                )

                stats = monitor.get_memory_stats()

                assert stats.percent_used == pytest.approx(0.5)
                mock_fallback.assert_called_once()

    def test_is_under_pressure_disabled(self, mock_logger):
        """Test that pressure detection can be disabled."""
        config = MemoryConfig(enable_adaptive_sizing=False)
        monitor = MemoryMonitor(config=config, logger=mock_logger)

        # Should always return False when disabled
        assert monitor.is_under_pressure() is False

    def test_pressure_state_accessors_track_enabled_decisions(self, mock_logger):
        """Operator-facing mode/state accessors expose the most recent decision."""
        monitor = MemoryMonitor(config=MemoryConfig(), logger=mock_logger)
        assert monitor.get_monitor_mode() == "unknown"
        assert monitor.get_last_pressure_state() is None

        with patch.object(monitor, "get_memory_stats") as get_stats:
            get_stats.return_value = MemoryStats(
                used_mb=7200.0,
                available_mb=800.0,
                total_mb=8000.0,
                percent_used=0.9,
                process_mb=256.0,
            )
            assert monitor.is_under_pressure() is True
            assert monitor.get_last_pressure_state() is True

            get_stats.return_value = MemoryStats(
                used_mb=3200.0,
                available_mb=4800.0,
                total_mb=8000.0,
                percent_used=0.4,
                process_mb=256.0,
            )
            assert monitor.is_under_pressure() is False
            assert monitor.get_last_pressure_state() is False

    def test_get_recommended_batch_size_no_pressure(self, mock_logger):
        """Test batch size unchanged when no pressure."""
        config = MemoryConfig(memory_pressure_threshold=0.9)
        monitor = MemoryMonitor(config=config, logger=mock_logger)

        with patch.object(monitor, "get_memory_stats") as mock_stats:
            mock_stats.return_value = MemoryStats(
                used_mb=4000.0,
                available_mb=4000.0,
                total_mb=8000.0,
                percent_used=0.5,  # Below threshold
                process_mb=256.0,
            )

            recommended = monitor.get_recommended_batch_size(1000)

            assert recommended == 1000

    def test_get_recommended_batch_size_under_pressure(self, mock_logger):
        """Test batch size reduced under pressure."""
        config = MemoryConfig(
            memory_pressure_threshold=0.8,
            min_batch_size=10,
        )
        monitor = MemoryMonitor(config=config, logger=mock_logger)

        with patch.object(monitor, "get_memory_stats") as mock_stats:
            mock_stats.return_value = MemoryStats(
                used_mb=7000.0,
                available_mb=1000.0,
                total_mb=8000.0,
                percent_used=0.875,  # Above threshold
                process_mb=256.0,
            )

            recommended = monitor.get_recommended_batch_size(1000)

            # Should be reduced by factor (0.5 for first pressure)
            assert recommended == 500

    def test_get_recommended_batch_size_respects_minimum(self, mock_logger):
        """Test batch size doesn't go below minimum."""
        config = MemoryConfig(
            memory_pressure_threshold=0.8,
            min_batch_size=50,
        )
        monitor = MemoryMonitor(config=config, logger=mock_logger)

        with patch.object(monitor, "get_memory_stats") as mock_stats:
            mock_stats.return_value = MemoryStats(
                used_mb=7000.0,
                available_mb=1000.0,
                total_mb=8000.0,
                percent_used=0.875,
                process_mb=256.0,
            )

            # With a small batch size, reduction should respect minimum
            recommended = monitor.get_recommended_batch_size(60)

            assert recommended >= config.min_batch_size

    def test_consecutive_pressure_increases_reduction(self, mock_logger):
        """Test that consecutive pressure increases reduction factor."""
        config = MemoryConfig(
            memory_pressure_threshold=0.8,
            min_batch_size=10,
        )
        monitor = MemoryMonitor(config=config, logger=mock_logger)

        with patch.object(monitor, "get_memory_stats") as mock_stats:
            mock_stats.return_value = MemoryStats(
                used_mb=7000.0,
                available_mb=1000.0,
                total_mb=8000.0,
                percent_used=0.875,
                process_mb=256.0,
            )

            # First call - 50% reduction
            size1 = monitor.get_recommended_batch_size(1000)
            assert size1 == 500

            # Second call - still 50% from current
            size2 = monitor.get_recommended_batch_size(500)
            assert size2 == 250

            # Third call - now 35% reduction factor kicks in
            size3 = monitor.get_recommended_batch_size(250)
            assert size3 == int(250 * 0.35)  # 87

    def test_pressure_relief_resets_counter(self, mock_logger):
        """Test that pressure relief resets the consecutive counter."""
        config = MemoryConfig(
            memory_pressure_threshold=0.8,
            min_batch_size=10,
        )
        monitor = MemoryMonitor(config=config, logger=mock_logger)

        with patch.object(monitor, "get_memory_stats") as mock_stats:
            # First call under pressure
            mock_stats.return_value = MemoryStats(
                used_mb=7000.0,
                available_mb=1000.0,
                total_mb=8000.0,
                percent_used=0.875,
                process_mb=256.0,
            )
            monitor.get_recommended_batch_size(1000)
            assert monitor._consecutive_pressure_count == 1

            # Second call with no pressure
            mock_stats.return_value = MemoryStats(
                used_mb=4000.0,
                available_mb=4000.0,
                total_mb=8000.0,
                percent_used=0.5,
                process_mb=256.0,
            )
            monitor.get_recommended_batch_size(500)
            assert monitor._consecutive_pressure_count == 0

    def test_estimate_batch_memory(self, monitor):
        """Test batch memory estimation."""
        memory_mb = monitor.estimate_batch_memory_mb(100, 1024)

        assert memory_mb == pytest.approx(0.244, rel=0.01)

    def test_calculate_max_batch_size(self, mock_logger):
        """Test max batch size calculation."""
        config = MemoryConfig(
            max_batch_memory_mb=256,
            min_batch_size=10,
        )
        monitor = MemoryMonitor(config=config, logger=mock_logger)

        max_size = monitor.calculate_max_batch_size(1024)

        assert max_size > 100000
        assert max_size < 110000

    def test_calculate_max_batch_size_respects_minimum(self, mock_logger):
        """Test max batch size respects minimum."""
        config = MemoryConfig(
            max_batch_memory_mb=1,  # Very small
            min_batch_size=100,
        )
        monitor = MemoryMonitor(config=config, logger=mock_logger)

        # With large records, calculated size might be below minimum
        max_size = monitor.calculate_max_batch_size(1024 * 1024)  # 1MB records

        assert max_size >= config.min_batch_size

    def test_disabled_adaptive_sizing_returns_original(self, mock_logger):
        """Test that disabled sizing returns original batch size."""
        config = MemoryConfig(enable_adaptive_sizing=False)
        monitor = MemoryMonitor(config=config, logger=mock_logger)

        with patch.object(monitor, "get_memory_stats") as mock_stats:
            mock_stats.return_value = MemoryStats(
                used_mb=7000.0,
                available_mb=1000.0,
                total_mb=8000.0,
                percent_used=0.95,  # Very high pressure
                process_mb=256.0,
            )

            recommended = monitor.get_recommended_batch_size(1000)

            # Should return original size even under pressure
            assert recommended == 1000


@pytest.mark.unit
class TestMemoryMonitorPsutil:
    """Tests for psutil-based memory monitoring."""

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        return MagicMock()

    def test_psutil_detection(self, mock_logger):
        """Test psutil availability detection."""
        config = MemoryConfig()
        monitor = MemoryMonitor(config=config, logger=mock_logger)

        # psutil should be detected (available or not based on environment)
        # This just verifies the check runs without error
        assert isinstance(monitor._psutil_available, bool)

    def test_get_stats_with_psutil(self, mock_logger):
        """Test stats retrieval with psutil (integration test)."""
        config = MemoryConfig()
        monitor = MemoryMonitor(config=config, logger=mock_logger)

        if not monitor._psutil_available:
            pytest.skip("psutil not available in this environment")

        stats = monitor._get_stats_psutil()

        assert stats.total_mb > 0
        assert stats.available_mb >= 0
        assert stats.used_mb >= 0
        assert 0 <= stats.percent_used <= 1
        assert stats.process_mb > 0

    def test_psutil_process_handle_is_cached(self, mock_logger, monkeypatch) -> None:
        """Repeated sampling reuses the expensive process handle."""
        process = MagicMock()
        process.memory_info.return_value = SimpleNamespace(rss=256 * 1024 * 1024)
        psutil = MagicMock()
        psutil.Process.return_value = process
        psutil.virtual_memory.return_value = SimpleNamespace(
            used=6 * 1024 * 1024,
            available=2 * 1024 * 1024,
            total=8 * 1024 * 1024,
            percent=75.0,
        )
        monkeypatch.setattr(memory_monitor_module, "_psutil_module", psutil)
        monitor = MemoryMonitor(config=MemoryConfig(), logger=mock_logger)
        monitor._psutil_available = True

        first = monitor.get_memory_stats()
        second = monitor.get_memory_stats()

        assert first == second
        assert monitor.get_monitor_mode() == "psutil"
        psutil.Process.assert_called_once_with()
        assert process.memory_info.call_count == 2


@pytest.mark.unit
class TestMemoryMonitorFallback:
    """Tests for fallback memory monitoring (graceful degradation)."""

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        return MagicMock()

    def test_get_stats_estimate_returns_conservative_values(self, mock_logger):
        """Test that fallback returns conservative estimates (50% usage).

        This tests the graceful degradation behavior documented in CLAUDE.md.
        When psutil is unavailable, the monitor returns safe estimates.
        """
        config = MemoryConfig()
        monitor = MemoryMonitor(config=config, logger=mock_logger)

        # Force use of estimate fallback
        stats = monitor._get_stats_estimate()

        # Should return 50% usage (conservative estimate)
        assert stats.percent_used == pytest.approx(0.5)
        assert stats.total_mb == pytest.approx(8192.0)  # 8GB assumed
        assert stats.used_mb == pytest.approx(4096.0)
        assert stats.available_mb == pytest.approx(4096.0)
        assert stats.process_mb == pytest.approx(256.0)  # 256MB assumed

    def test_get_stats_estimate_not_zeros(self, mock_logger):
        """Verify fallback doesn't return zeros (regression test for false claim).

        See: consolidated-refactoring-analysis.md - "MemoryMonitor returns zeros"
        was a FALSE claim. This test ensures graceful degradation works.
        """
        config = MemoryConfig()
        monitor = MemoryMonitor(config=config, logger=mock_logger)

        stats = monitor._get_stats_estimate()

        # All values must be > 0 (no zeros)
        assert stats.used_mb > 0
        assert stats.available_mb > 0
        assert stats.total_mb > 0
        assert stats.percent_used > 0
        assert stats.process_mb > 0


@pytest.mark.unit
class TestMemoryMonitorRecovery:
    """Tests for memory pressure recovery behavior."""

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        return MagicMock()

    def test_batch_size_recovery_after_pressure(self, mock_logger):
        """Test gradual batch size increase after pressure is relieved."""
        config = MemoryConfig(
            memory_pressure_threshold=0.8,
            min_batch_size=10,
        )
        monitor = MemoryMonitor(config=config, logger=mock_logger)

        with patch.object(monitor, "get_memory_stats") as mock_stats:
            # Phase 1: Under pressure - reduce batch size
            mock_stats.return_value = MemoryStats(
                used_mb=7000.0,
                available_mb=1000.0,
                total_mb=8000.0,
                percent_used=0.9,
                process_mb=256.0,
            )
            reduced = monitor.get_recommended_batch_size(1000)
            assert reduced == 500  # 50% reduction

            # Phase 2: Pressure relieved - gradual recovery
            mock_stats.return_value = MemoryStats(
                used_mb=4000.0,
                available_mb=4000.0,
                total_mb=8000.0,
                percent_used=0.5,  # Low usage
                process_mb=256.0,
            )
            recovered = monitor.get_recommended_batch_size(reduced)

            # Should increase by 25% but not exceed last known good size
            expected = min(int(reduced * 1.25), monitor._last_batch_size)
            assert recovered == expected

    def test_aggressive_reduction_at_5_plus_pressure(self, mock_logger):
        """Test aggressive 25% reduction factor after 5+ consecutive pressures."""
        config = MemoryConfig(
            memory_pressure_threshold=0.8,
            min_batch_size=10,
        )
        monitor = MemoryMonitor(config=config, logger=mock_logger)

        with patch.object(monitor, "get_memory_stats") as mock_stats:
            mock_stats.return_value = MemoryStats(
                used_mb=7000.0,
                available_mb=1000.0,
                total_mb=8000.0,
                percent_used=0.9,
                process_mb=256.0,
            )

            # Simulate 5+ consecutive pressure events
            current_size = 1000
            for _i in range(6):
                current_size = monitor.get_recommended_batch_size(current_size)

            # After 5+ pressure events, reduction should be 0.25
            assert monitor._consecutive_pressure_count >= 5
            # Verify the reduction factor
            assert monitor._get_reduction_factor() == pytest.approx(0.25)


@pytest.mark.unit
class TestMemoryMonitorResourceFallback:
    """Tests for resource module fallback on Unix systems."""

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        return MagicMock()

    def test_get_stats_fallback_windows_uses_estimate(self, mock_logger):
        """Test that Windows falls back to estimate."""
        config = MemoryConfig()
        monitor = MemoryMonitor(config=config, logger=mock_logger)

        with patch.object(monitor, "_psutil_available", False):
            with patch("bioetl.infrastructure.system.memory_monitor.sys") as mock_sys:
                mock_sys.platform = "win32"

                stats = monitor._get_stats_fallback()

                # Should use estimate
                assert stats.percent_used == pytest.approx(0.5)

    def test_get_stats_fallback_unix_uses_resource(self, mock_logger) -> None:
        """Non-Windows fallback delegates to the resource/procfs sampler."""
        monitor = MemoryMonitor(config=MemoryConfig(), logger=mock_logger)
        expected = MemoryStats(6.0, 2.0, 8.0, 0.75, 1.0)

        with (
            patch.object(memory_monitor_module.sys, "platform", "linux"),
            patch.object(
                monitor,
                "_get_stats_resource",
                return_value=expected,
            ) as get_resource,
        ):
            assert monitor._get_stats_fallback() == expected

        get_resource.assert_called_once_with()

    def test_logging_when_psutil_unavailable(self, mock_logger):
        """Test debug log when psutil is not available."""
        config = MemoryConfig()

        with patch(
            "bioetl.infrastructure.system.memory_monitor._check_psutil_available"
        ) as mock_check:
            mock_check.return_value = False
            monitor = MemoryMonitor(config=config, logger=mock_logger)

            assert monitor._psutil_available is False

    def test_resource_fallback_parses_linux_meminfo(
        self,
        mock_logger,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Unix fallback reports process and host values without psutil."""
        pytest.importorskip("resource")
        meminfo = "MemTotal: 8192 kB\nMemAvailable: 2048 kB\n"
        monkeypatch.setattr(
            memory_monitor_module.Path,
            "open",
            lambda *_args, **_kwargs: StringIO(meminfo),
        )
        monitor = MemoryMonitor(config=MemoryConfig(), logger=mock_logger)

        with patch(
            "resource.getrusage",
            return_value=SimpleNamespace(ru_maxrss=1024),
        ):
            stats = monitor._get_stats_resource()

        assert monitor.get_monitor_mode() == "resource"
        assert stats.total_mb == pytest.approx(8.0)
        assert stats.available_mb == pytest.approx(2.0)
        assert stats.used_mb == pytest.approx(6.0)
        assert stats.percent_used == pytest.approx(0.75)
        assert stats.process_mb == pytest.approx(1.0)

    def test_resource_fallback_uses_estimate_when_meminfo_is_unreadable(
        self,
        mock_logger,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Unreadable procfs degrades to deterministic conservative estimates."""
        pytest.importorskip("resource")
        monkeypatch.setattr(
            memory_monitor_module.Path,
            "open",
            MagicMock(side_effect=OSError("procfs unavailable")),
        )
        monitor = MemoryMonitor(config=MemoryConfig(), logger=mock_logger)

        with patch(
            "resource.getrusage",
            return_value=SimpleNamespace(ru_maxrss=1024),
        ):
            stats = monitor._get_stats_resource()

        assert monitor.get_monitor_mode() == "estimate"
        assert stats.percent_used == pytest.approx(0.5)

    def test_recovery_completion_and_pressure_reduction_work_without_logger(
        self,
    ) -> None:
        """Adaptive sizing is functional even when no structured logger is injected."""
        monitor = MemoryMonitor(config=MemoryConfig(), logger=None)
        low = MemoryStats(4000.0, 4000.0, 8000.0, 0.5, 256.0)
        high = MemoryStats(7200.0, 800.0, 8000.0, 0.9, 256.0)
        monitor._recovery_target_batch_size = 101
        monitor._last_batch_size = 101

        with patch.object(monitor, "get_memory_stats", return_value=low):
            assert monitor.get_recommended_batch_size(100) == 101
        assert monitor._recovery_target_batch_size is None
        assert monitor._last_batch_size == 101

        with patch.object(monitor, "get_memory_stats", return_value=high):
            assert monitor.get_recommended_batch_size(100) == 50
