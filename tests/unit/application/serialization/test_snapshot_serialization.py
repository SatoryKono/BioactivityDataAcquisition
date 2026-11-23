"""Snapshots normalize nested data without leaking private object attributes."""

from __future__ import annotations

import pytest
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from uuid import UUID
from bioetl.application.serialization.snapshot_serialization import (
    normalize_snapshot,
    to_serializable_mapping,
)


pytestmark = pytest.mark.unit


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


def test_pydantic_snapshot_omits_unset_defaults_for_dq_replay():
    """Manifest serialization must not materialize unset DQ defaults."""
    from bioetl.infrastructure.schemas.pipeline_config_dq import (
        DQYamlConfig as InlineDQConfig,
    )

    empty = InlineDQConfig.model_validate({})
    dumped = to_serializable_mapping(empty)
    restored = InlineDQConfig.model_validate(dumped)
    assert restored.model_fields_set == set()
    assert "soft_fail_threshold" not in dumped
    assert "hard_fail_threshold" not in dumped

    partial = InlineDQConfig.model_validate({"soft_fail_threshold": 0.25})
    partial_dump = to_serializable_mapping(partial)
    assert partial_dump == {"soft_fail_threshold": 0.25}
    restored_partial = InlineDQConfig.model_validate(partial_dump)
    assert restored_partial.model_fields_set == {"soft_fail_threshold"}
    assert restored_partial.soft_fail_threshold == 0.25
