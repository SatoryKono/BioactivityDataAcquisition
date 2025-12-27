"""Unit tests for MemoryMonitor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bioetl.application.core.memory_monitor import (
    MemoryConfig,
    MemoryMonitor,
    MemoryStats,
)


@pytest.mark.unit
class TestMemoryConfig:
    """Tests for MemoryConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = MemoryConfig()

        assert config.max_batch_memory_mb == 512
        assert config.memory_pressure_threshold == 0.8
        assert config.min_batch_size == 10
        assert config.check_interval_records == 100
        assert config.enable_adaptive_sizing is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = MemoryConfig(
            max_batch_memory_mb=1024,
            memory_pressure_threshold=0.9,
            min_batch_size=5,
            check_interval_records=50,
            enable_adaptive_sizing=False,
        )

        assert config.max_batch_memory_mb == 1024
        assert config.memory_pressure_threshold == 0.9
        assert config.min_batch_size == 5
        assert config.check_interval_records == 50
        assert config.enable_adaptive_sizing is False


@pytest.mark.unit
class TestMemoryStats:
    """Tests for MemoryStats dataclass."""

    def test_is_under_pressure_high_usage(self):
        """Test that high memory usage is detected as pressure."""
        stats = MemoryStats(
            used_mb=7000.0,
            available_mb=1000.0,
            total_mb=8000.0,
            percent_used=0.875,
            process_mb=500.0,
        )

        assert stats.is_under_pressure is True

    def test_is_under_pressure_low_usage(self):
        """Test that low memory usage is not pressure."""
        stats = MemoryStats(
            used_mb=4000.0,
            available_mb=4000.0,
            total_mb=8000.0,
            percent_used=0.5,
            process_mb=500.0,
        )

        assert stats.is_under_pressure is False

    def test_is_under_pressure_boundary(self):
        """Test boundary condition at 80%."""
        stats_exactly_80 = MemoryStats(
            used_mb=6400.0,
            available_mb=1600.0,
            total_mb=8000.0,
            percent_used=0.8,
            process_mb=500.0,
        )

        # Exactly 80% should not be under pressure (> 0.8, not >=)
        assert stats_exactly_80.is_under_pressure is False

        stats_over_80 = MemoryStats(
            used_mb=6401.0,
            available_mb=1599.0,
            total_mb=8000.0,
            percent_used=0.801,
            process_mb=500.0,
        )

        assert stats_over_80.is_under_pressure is True


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

                assert stats.percent_used == 0.5
                mock_fallback.assert_called_once()

    def test_is_under_pressure_disabled(self, mock_logger):
        """Test that pressure detection can be disabled."""
        config = MemoryConfig(enable_adaptive_sizing=False)
        monitor = MemoryMonitor(config=config, logger=mock_logger)

        # Should always return False when disabled
        assert monitor.is_under_pressure() is False

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
        # 100 records * 1KB * 2.5 overhead = 250KB = 0.244MB
        memory_mb = monitor.estimate_batch_memory_mb(100, 1024)

        assert memory_mb == pytest.approx(0.244, rel=0.01)

    def test_calculate_max_batch_size(self, mock_logger):
        """Test max batch size calculation."""
        config = MemoryConfig(
            max_batch_memory_mb=256,
            min_batch_size=10,
        )
        monitor = MemoryMonitor(config=config, logger=mock_logger)

        # 256MB / (1KB * 2.5) = 104857 records
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

    @pytest.mark.skipif(
        True,  # Skip in CI - psutil may not be installed
        reason="psutil may not be available in test environment",
    )
    def test_get_stats_with_psutil(self, mock_logger):
        """Test stats retrieval with psutil (integration test)."""
        config = MemoryConfig()
        monitor = MemoryMonitor(config=config, logger=mock_logger)

        if monitor._psutil_available:
            stats = monitor._get_stats_psutil()

            assert stats.total_mb > 0
            assert stats.available_mb >= 0
            assert stats.used_mb >= 0
            assert 0 <= stats.percent_used <= 1
            assert stats.process_mb > 0
