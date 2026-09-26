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
"""Replay-safe serialization and immutability tests for ledger core events."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from bioetl.domain.control_plane.ledger import LedgerEvent
from bioetl.domain.serialization import serialize_to_json_canonical

pytestmark = pytest.mark.unit


def _build_event() -> LedgerEvent:
    return LedgerEvent(
        event_type="contract_registry_updated",
        timestamp="2026-06-16T12:05:00Z",
        run_id="run-456",
        data={
            "nested": {"z": 1, "a": 2},
            "contract_ref": "chembl.activity.v1",
            "version": "1.0.0",
        },
    )


def test_ledger_event_to_mapping_sorts_payload_keys() -> None:
    event = _build_event()

    mapping = event.to_mapping()

    assert mapping == {
        "data": {
            "contract_ref": "chembl.activity.v1",
            "nested": {"a": 2, "z": 1},
            "version": "1.0.0",
        },
        "event_type": "contract_registry_updated",
        "run_id": "run-456",
        "timestamp": "2026-06-16T12:05:00Z",
    }


def test_ledger_event_to_mapping_round_trips_through_canonical_json() -> None:
    event = _build_event()

    first = serialize_to_json_canonical(event.to_mapping())
    second = serialize_to_json_canonical(event.to_mapping())

    assert first == second
    assert first == (
        '{"data":{"contract_ref":"chembl.activity.v1","nested":{"a":2,"z":1},'
        '"version":"1.0.0"},"event_type":"contract_registry_updated",'
        '"run_id":"run-456","timestamp":"2026-06-16T12:05:00Z"}'
    )


def test_ledger_event_remains_immutable_after_to_mapping() -> None:
    event = LedgerEvent(
        event_type="manifest_written",
        timestamp="2026-06-16T12:00:00Z",
        run_id="run-immutable",
        data={"stage": "seed"},
    )

    _ = event.to_mapping()

    with pytest.raises(FrozenInstanceError):
        event.event_type = "mutated"  # type: ignore[misc]


def test_ledger_event_empty_data_serializes_to_empty_object() -> None:
    event = LedgerEvent(
        event_type="manifest_written",
        timestamp="2026-06-16T12:00:00Z",
        run_id="run-empty",
    )

    assert event.to_mapping()["data"] == {}
