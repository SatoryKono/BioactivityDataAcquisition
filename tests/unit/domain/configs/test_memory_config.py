"""Unit tests for MemoryConfig domain configuration."""

from __future__ import annotations

import pytest

from bioetl.domain.config.memory import MemoryConfig


@pytest.mark.unit
class TestMemoryConfig:
    """Tests for MemoryConfig dataclass."""

    def test_default_values(self) -> None:
        mc = MemoryConfig()
        assert mc.max_batch_memory_mb == 512
        assert mc.memory_pressure_threshold == pytest.approx(0.8)
        assert mc.min_batch_size == 10
        assert mc.check_interval_records == 100
        assert mc.enable_adaptive_sizing is True

    def test_custom_values(self) -> None:
        mc = MemoryConfig(
            max_batch_memory_mb=1024,
            memory_pressure_threshold=0.9,
            min_batch_size=5,
            check_interval_records=50,
            enable_adaptive_sizing=False,
        )
        assert mc.max_batch_memory_mb == 1024
        assert mc.memory_pressure_threshold == pytest.approx(0.9)
        assert mc.enable_adaptive_sizing is False

    def test_immutable(self) -> None:
        mc = MemoryConfig()
        with pytest.raises((AttributeError, TypeError)):
            mc.max_batch_memory_mb = 256  # type: ignore[misc]

    def test_equality(self) -> None:
        mc1 = MemoryConfig()
        mc2 = MemoryConfig()
        assert mc1 == mc2

    def test_inequality(self) -> None:
        mc1 = MemoryConfig(max_batch_memory_mb=512)
        mc2 = MemoryConfig(max_batch_memory_mb=1024)
        assert mc1 != mc2

    def test_hashable(self) -> None:
        mc = MemoryConfig()
        assert hash(mc) == hash(MemoryConfig())
        s = {mc}
        assert len(s) == 1

    def test_edge_case_zero_threshold(self) -> None:
        mc = MemoryConfig(memory_pressure_threshold=0.0)
        assert mc.memory_pressure_threshold == pytest.approx(0.0)

    def test_edge_case_one_threshold(self) -> None:
        mc = MemoryConfig(memory_pressure_threshold=1.0)
        assert mc.memory_pressure_threshold == pytest.approx(1.0)
