# pyright: reportArgumentType=false
"""Unit tests for snapshot mapping serialization helpers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

import pytest

from bioetl.composition.runtime_builders._snapshot_mapping_support import (
    normalize_snapshot,
    to_serializable_mapping,
)

pytestmark = pytest.mark.unit


class _SampleEnum(Enum):
    ALPHA = "alpha"
    BETA = "beta"


@dataclass
class _SampleDataclass:
    name: str
    count: int


class _ModelDumpHost:
    def model_dump(self, *, mode: str = "python", exclude_none: bool = False):
        del mode, exclude_none
        return {"kind": "model", "value": 1}


class _DictHost:
    def dict(self, *, exclude_none: bool = False):
        del exclude_none
        return {"kind": "dict", "value": 2}


def test_normalize_snapshot_dataclass_enum_uuid() -> None:
    sample_uuid = UUID("12345678-1234-5678-1234-567812345678")
    payload = normalize_snapshot(
        {
            "dc": _SampleDataclass(name="x", count=3),
            "flag": _SampleEnum.ALPHA,
            "id": sample_uuid,
            "items": {_SampleEnum.BETA, "z"},
        }
    )
    assert isinstance(payload, dict)
    assert payload["dc"] == {"name": "x", "count": 3}
    assert payload["flag"] == "alpha"
    assert payload["id"] == "12345678-1234-5678-1234-567812345678"
    assert set(payload["items"]) == {"beta", "z"}  # type: ignore[arg-type]


def test_to_serializable_mapping_model_dump_and_dict() -> None:
    assert to_serializable_mapping(_ModelDumpHost()) == {"kind": "model", "value": 1}
    assert to_serializable_mapping(_DictHost()) == {"kind": "dict", "value": 2}


def test_to_serializable_mapping_non_mapping_wraps_value() -> None:
    assert to_serializable_mapping("plain") == {"value": "plain"}
