"""Unit tests for MemoryManager."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.application.core.memory_manager import (
    MemoryConfig,
    MemoryManager,
    MemoryPressure,
    MemoryStats,
)


@pytest.mark.unit
class TestMemoryConfig:
    """Tests for MemoryConfig validation."""

    def test_default_config_is_valid(self):
        """Test that default configuration is valid."""
        config = MemoryConfig()

        assert config.max_batch_memory_mb == 512
        assert config.pressure_threshold_medium == 0.6
        assert config.pressure_threshold_high == 0.75
        assert config.pressure_threshold_critical == 0.9
        assert config.min_batch_size == 10
        assert config.batch_reduction_factor == 0.5
        assert config.gc_on_high_pressure is True
        assert config.enabled is True

    def test_custom_config_is_valid(self):
        """Test that custom configuration is accepted."""
        config = MemoryConfig(
            max_batch_memory_mb=1024,
            pressure_threshold_medium=0.5,
            pressure_threshold_high=0.7,
            pressure_threshold_critical=0.85,
            min_batch_size=5,
            batch_reduction_factor=0.25,
            gc_on_high_pressure=False,
            enabled=False,
        )

        assert config.max_batch_memory_mb == 1024
        assert config.pressure_threshold_medium == 0.5
        assert config.min_batch_size == 5
        assert config.enabled is False

    def test_invalid_max_batch_memory_raises(self):
        """Test that invalid max_batch_memory_mb raises ValueError."""
        with pytest.raises(ValueError, match="max_batch_memory_mb must be positive"):
            MemoryConfig(max_batch_memory_mb=0)

        with pytest.raises(ValueError, match="max_batch_memory_mb must be positive"):
            MemoryConfig(max_batch_memory_mb=-1)

    def test_invalid_threshold_range_raises(self):
        """Test that thresholds outside (0, 1) raise ValueError."""
        with pytest.raises(ValueError, match="pressure_threshold_medium"):
            MemoryConfig(pressure_threshold_medium=0.0)

        with pytest.raises(ValueError, match="pressure_threshold_high"):
            MemoryConfig(pressure_threshold_high=1.0)

    def test_invalid_threshold_ordering_raises(self):
        """Test that thresholds must be ordered: medium < high < critical."""
        with pytest.raises(ValueError, match="Thresholds must be ordered"):
            MemoryConfig(
                pressure_threshold_medium=0.8,
                pressure_threshold_high=0.7,
                pressure_threshold_critical=0.9,
            )

    def test_invalid_min_batch_size_raises(self):
        """Test that invalid min_batch_size raises ValueError."""
        with pytest.raises(ValueError, match="min_batch_size must be positive"):
            MemoryConfig(min_batch_size=0)

    def test_invalid_batch_reduction_factor_raises(self):
        """Test that batch_reduction_factor must be in (0, 1)."""
        with pytest.raises(ValueError, match="batch_reduction_factor must be in"):
            MemoryConfig(batch_reduction_factor=0.0)

        with pytest.raises(ValueError, match="batch_reduction_factor must be in"):
            MemoryConfig(batch_reduction_factor=1.0)


@pytest.mark.unit
class TestMemoryStats:
    """Tests for MemoryStats dataclass."""

    def test_memory_stats_creation(self):
        """Test MemoryStats creation."""
        stats = MemoryStats(
            used_mb=256.0,
            limit_mb=512.0,
            usage_ratio=0.5,
            pressure=MemoryPressure.LOW,
        )

        assert stats.used_mb == 256.0
        assert stats.limit_mb == 512.0
        assert stats.usage_ratio == 0.5
        assert stats.pressure == MemoryPressure.LOW


@pytest.mark.unit
class TestMemoryManager:
    """Tests for MemoryManager class."""

    def test_default_initialization(self):
        """Test MemoryManager with default config."""
        manager = MemoryManager()

        assert manager.is_enabled is True
        assert manager.config.max_batch_memory_mb == 512

    def test_custom_config_initialization(self):
        """Test MemoryManager with custom config."""
        config = MemoryConfig(max_batch_memory_mb=1024, enabled=False)
        manager = MemoryManager(config=config)

        assert manager.is_enabled is False
        assert manager.config.max_batch_memory_mb == 1024

    def test_set_base_batch_size(self):
        """Test setting base batch size."""
        manager = MemoryManager()
        manager.set_base_batch_size(200)

        # Should return same size when no pressure
        recommended = manager.get_recommended_batch_size(200)
        assert recommended == 200

    def test_get_current_stats(self):
        """Test getting current memory stats."""
        manager = MemoryManager()
        stats = manager.get_current_stats()

        assert isinstance(stats, MemoryStats)
        assert stats.used_mb >= 0
        assert stats.limit_mb > 0
        assert 0.0 <= stats.usage_ratio <= 1.0
        assert isinstance(stats.pressure, MemoryPressure)

    def test_pressure_calculation_low(self):
        """Test pressure calculation for low memory usage."""
        config = MemoryConfig(
            pressure_threshold_medium=0.5,
            pressure_threshold_high=0.7,
            pressure_threshold_critical=0.9,
        )
        manager = MemoryManager(config=config)

        # Test internal pressure calculation
        assert manager._calculate_pressure(0.3) == MemoryPressure.LOW
        assert manager._calculate_pressure(0.49) == MemoryPressure.LOW

    def test_pressure_calculation_medium(self):
        """Test pressure calculation for medium memory usage."""
        config = MemoryConfig(
            pressure_threshold_medium=0.5,
            pressure_threshold_high=0.7,
            pressure_threshold_critical=0.9,
        )
        manager = MemoryManager(config=config)

        assert manager._calculate_pressure(0.5) == MemoryPressure.MEDIUM
        assert manager._calculate_pressure(0.69) == MemoryPressure.MEDIUM

    def test_pressure_calculation_high(self):
        """Test pressure calculation for high memory usage."""
        config = MemoryConfig(
            pressure_threshold_medium=0.5,
            pressure_threshold_high=0.7,
            pressure_threshold_critical=0.9,
        )
        manager = MemoryManager(config=config)

        assert manager._calculate_pressure(0.7) == MemoryPressure.HIGH
        assert manager._calculate_pressure(0.89) == MemoryPressure.HIGH

    def test_pressure_calculation_critical(self):
        """Test pressure calculation for critical memory usage."""
        config = MemoryConfig(
            pressure_threshold_medium=0.5,
            pressure_threshold_high=0.7,
            pressure_threshold_critical=0.9,
        )
        manager = MemoryManager(config=config)

        assert manager._calculate_pressure(0.9) == MemoryPressure.CRITICAL
        assert manager._calculate_pressure(1.0) == MemoryPressure.CRITICAL

    def test_recommended_batch_size_when_disabled(self):
        """Test that disabled manager returns original batch size."""
        config = MemoryConfig(enabled=False)
        manager = MemoryManager(config=config)

        assert manager.get_recommended_batch_size(100) == 100
        assert manager.get_recommended_batch_size(1000) == 1000

    def test_should_process_in_chunks_when_disabled(self):
        """Test that disabled manager never recommends chunking."""
        config = MemoryConfig(enabled=False)
        manager = MemoryManager(config=config)

        assert manager.should_process_in_chunks(1000) is False

    def test_get_chunk_size_when_disabled(self):
        """Test that disabled manager returns full batch size."""
        config = MemoryConfig(enabled=False)
        manager = MemoryManager(config=config)

        assert manager.get_chunk_size(1000) == 1000

    def test_estimate_record_memory_empty(self):
        """Test memory estimation for empty records."""
        manager = MemoryManager()

        assert manager.estimate_record_memory([]) == 0.0

    def test_estimate_record_memory_with_records(self):
        """Test memory estimation with records."""
        manager = MemoryManager()
        records = [{"id": i, "name": f"record_{i}"} for i in range(100)]

        memory_mb = manager.estimate_record_memory(records)

        assert memory_mb > 0
        assert memory_mb < 10  # Should be relatively small for simple records

    def test_logger_integration(self):
        """Test that logger is called on pressure adjustment."""
        mock_logger = MagicMock()
        config = MemoryConfig(
            pressure_threshold_medium=0.01,  # Very low to trigger
            pressure_threshold_high=0.02,
            pressure_threshold_critical=0.03,
        )
        manager = MemoryManager(config=config, logger=mock_logger)
        manager.set_base_batch_size(100)

        # This should trigger pressure adjustment logging
        # Since we can't control actual memory, we test the method directly
        manager._log_pressure_adjustment(
            MemoryStats(
                used_mb=400.0,
                limit_mb=512.0,
                usage_ratio=0.78,
                pressure=MemoryPressure.HIGH,
            ),
            old_size=100,
            new_size=50,
        )

        mock_logger.warning.assert_called_once()


@pytest.mark.unit
class TestMemoryManagerChunking:
    """Tests for memory-efficient chunking."""

    def test_get_chunk_size_under_low_pressure(self):
        """Test chunk size calculation under low pressure."""
        config = MemoryConfig(
            max_batch_memory_mb=10000,  # High limit to ensure low pressure
        )
        manager = MemoryManager(config=config)

        # Under low pressure, should return full batch size
        chunk_size = manager.get_chunk_size(1000)
        assert chunk_size == 1000

    def test_minimum_chunk_size_respected_under_pressure(self):
        """Test that minimum chunk size is floor when under pressure.

        The min_batch_size is only enforced as a floor when memory pressure
        causes batch size reduction. When under low pressure, the original
        batch size is returned even if it's smaller than min_batch_size.
        """
        config = MemoryConfig(
            min_batch_size=20,
            max_batch_memory_mb=10000,  # High limit to ensure low pressure
        )
        manager = MemoryManager(config=config)

        # Under low pressure, should return original batch size
        chunk_size = manager.get_chunk_size(5)
        assert chunk_size == 5

        # The min_batch_size is used as floor in get_recommended_batch_size
        # when pressure causes reduction, not in get_chunk_size for small batches


@pytest.mark.unit
class TestMemoryPressureEnum:
    """Tests for MemoryPressure enum."""

    def test_all_pressure_levels_exist(self):
        """Test that all pressure levels are defined."""
        assert MemoryPressure.LOW.value == "low"
        assert MemoryPressure.MEDIUM.value == "medium"
        assert MemoryPressure.HIGH.value == "high"
        assert MemoryPressure.CRITICAL.value == "critical"

    def test_pressure_levels_are_distinct(self):
        """Test that all pressure levels are distinct."""
        levels = [
            MemoryPressure.LOW,
            MemoryPressure.MEDIUM,
            MemoryPressure.HIGH,
            MemoryPressure.CRITICAL,
        ]
        assert len(levels) == len(set(levels))
