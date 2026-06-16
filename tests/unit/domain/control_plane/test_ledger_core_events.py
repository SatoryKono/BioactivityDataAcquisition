"""Unit tests for legacy control-plane ledger event surfaces."""

from __future__ import annotations

import pytest

from bioetl.domain.control_plane.ledger import LedgerEvent


pytestmark = pytest.mark.unit


def test_ledger_package_reexports_core_event_value_object() -> None:
    """Legacy package surface should re-export the canonical event type."""
    event = LedgerEvent(
        event_type="manifest_written",
        timestamp="2026-06-16T12:00:00Z",
        run_id="run-123",
    )

    assert event.event_type == "manifest_written"
    assert event.timestamp == "2026-06-16T12:00:00Z"
    assert event.run_id == "run-123"
    assert event.data == {}


def test_ledger_event_accepts_explicit_payload_mapping() -> None:
    """Ledger events should preserve explicit append-only payload dictionaries."""
    payload = {"contract_ref": "chembl.activity.v1", "version": "1.0.0"}

    event = LedgerEvent(
        event_type="contract_registry_updated",
        timestamp="2026-06-16T12:05:00Z",
        run_id="run-456",
        data=payload,
    )

    assert event.data == payload
