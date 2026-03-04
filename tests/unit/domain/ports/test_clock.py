"""Unit tests for ClockPort protocol."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.domain.ports import ClockPort


class _ClockStub:
    def now(self) -> datetime:
        return datetime.now(UTC)


@pytest.mark.unit
def test_clock_port_is_runtime_checkable() -> None:
    """ClockPort supports isinstance checks via runtime_checkable."""
    assert isinstance(_ClockStub(), ClockPort)


@pytest.mark.unit
def test_clock_port_exported_in_ports_facade() -> None:
    """ClockPort is exported by bioetl.domain.ports facade."""
    import bioetl.domain.ports as ports

    assert "ClockPort" in ports.__all__
    assert ports.ClockPort is ClockPort
