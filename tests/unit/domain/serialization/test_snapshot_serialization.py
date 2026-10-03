"""Snapshots normalize nested data without leaking private object attributes."""

from __future__ import annotations
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from uuid import UUID
from bioetl.domain.serialization.snapshot_serialization import (
    normalize_snapshot,
    to_serializable_mapping,
)


@dataclass
class Snapshot:
    duration: timedelta
    amount: Decimal


def test_nested_dataclass_values_are_json_primitives():
    assert normalize_snapshot(
        {
            "nested": Snapshot(timedelta(seconds=2), Decimal("1.20")),
            "ids": (UUID(int=0),),
        }
    ) == {"nested": {"duration": 2.0, "amount": "1.20"}, "ids": [str(UUID(int=0))]}


def test_object_payload_excludes_private_state_and_wraps_scalars():
    class Payload:
        def __init__(self):
            self.public = Decimal("2")
            self._secret = "hidden"

    assert to_serializable_mapping(Payload()) == {"public": "2"}
    assert to_serializable_mapping(Decimal("3")) == {"value": "3"}
