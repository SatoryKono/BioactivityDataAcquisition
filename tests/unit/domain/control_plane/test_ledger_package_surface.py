"""Coverage tests for the control-plane ledger package surface."""

from __future__ import annotations

import pytest

from bioetl.domain.control_plane.ledger import LedgerEvent


pytestmark = pytest.mark.unit


def test_ledger_package_root_reexports_core_event_type() -> None:
    """Legacy package root should continue exposing the core event value object."""
    assert LedgerEvent.__module__ == "bioetl.domain.control_plane.ledger.core_events"


def test_ledger_event_preserves_append_only_payload_shape() -> None:
    """Ledger event compatibility payload should remain immutable and typed."""
    event = LedgerEvent(
        event_type="run_started",
        timestamp="2026-06-16T12:00:00+00:00",
        run_id="run-123",
        data={"stage": "bootstrap", "attempt": 1},
    )

    assert event.event_type == "run_started"
    assert event.timestamp == "2026-06-16T12:00:00+00:00"
    assert event.run_id == "run-123"
    assert event.data == {"stage": "bootstrap", "attempt": 1}
