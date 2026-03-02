"""Unit tests for delta_writer compatibility wrapper.

Verifies that the re-export wrapper correctly exposes DeltaWriter and
SilverWriteMode for backward compatibility with legacy import paths.
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestDeltaWriterCompat:
    """Tests for delta_writer.py compatibility wrapper."""

    def test_delta_writer_importable(self) -> None:
        """DeltaWriter can be imported from delta_writer module."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter

        assert DeltaWriter is not None

    def test_silver_write_mode_importable(self) -> None:
        """SilverWriteMode can be imported from delta_writer module."""
        from bioetl.infrastructure.storage.delta_writer import SilverWriteMode

        assert SilverWriteMode is not None

    def test_delta_writer_is_silver_writer(self) -> None:
        """DeltaWriter is an alias for SilverWriter."""
        from bioetl.infrastructure.storage.delta_writer import DeltaWriter
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        assert DeltaWriter is SilverWriter

    def test_silver_write_mode_from_delta_equals_domain(self) -> None:
        """SilverWriteMode exported from delta_writer matches domain medallion."""
        from bioetl.infrastructure.storage.delta_writer import SilverWriteMode
        from bioetl.domain.medallion import SilverWriteMode as DomainSilverWriteMode

        assert SilverWriteMode is DomainSilverWriteMode

    def test_system_module_init_exports_memory_monitor(self) -> None:
        """MemoryMonitor is exported from infrastructure.system package."""
        from bioetl.infrastructure.system import MemoryMonitor

        assert MemoryMonitor is not None

    def test_system_all_exports(self) -> None:
        """__all__ in system package contains MemoryMonitor."""
        import bioetl.infrastructure.system as sys_pkg

        assert "MemoryMonitor" in sys_pkg.__all__
