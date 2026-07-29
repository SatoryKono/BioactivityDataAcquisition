# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Unit tests for legacy control-plane ledger event surfaces."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import UUID

import pytest

from bioetl.domain.control_plane.ledger import LedgerEvent
from bioetl.domain.control_plane.run_ledger import RunLedgerEntry
from bioetl.domain.types import RunID


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


def test_ledger_event_is_immutable_after_creation() -> None:
    """Ledger events are append-only value objects."""
    event = LedgerEvent(
        event_type="manifest_written",
        timestamp="2026-06-16T12:00:00Z",
        run_id="run-immutable",
    )

    with pytest.raises(FrozenInstanceError):
        event.event_type = "mutated"  # type: ignore[misc]


def test_run_ledger_entry_serialization_is_json_safe_and_deterministic() -> None:
    """Nested ledger details should serialize with stable key and set ordering."""
    run_id = RunID(UUID("12345678-1234-5678-1234-567812345678"))
    entry = RunLedgerEntry(
        entry_id="entry-1",
        manifest_id="manifest-1",
        run_id=run_id,
        event_type="stage_completed",
        occurred_at=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
        stage=" Seed ",
        metrics_snapshot={"silver_rows": 5},
        details={
            "unordered_tags": {"b", "a"},
            "nested": {"z": 1, "a": 2},
        },
    )

    payload = entry.to_dict()

    assert payload["run_id"] == str(run_id)
    assert payload["occurred_at"] == "2026-06-16T12:00:00Z"
    assert payload["stage"] == "seed"
    assert payload["details"] == {
        "nested": {"a": 2, "z": 1},
        "unordered_tags": ["a", "b"],
    }
    assert RunLedgerEntry.from_dict(payload).to_dict() == payload
