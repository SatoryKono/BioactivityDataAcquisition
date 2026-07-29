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
"""Focused branch coverage for control-plane primitive normalization helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import Enum
from uuid import UUID

import pytest

from bioetl.domain.normalization import _control_plane_primitives as primitives


pytestmark = pytest.mark.unit


class _Token(Enum):
    VALUE = "token-value"


@dataclass(frozen=True)
class _Payload:
    when: datetime
    ids: frozenset[int]
    token: _Token


def test_control_plane_primitive_normalizers_cover_optional_and_scalar_edges() -> None:
    run_id = UUID("00000000-0000-0000-0000-000000000123")
    assert primitives.normalize_control_plane_uuid(run_id) == str(run_id)
    assert primitives.normalize_control_plane_uuid(f" {run_id} ") == str(run_id)
    assert (
        primitives.normalize_control_plane_datetime(datetime(2026, 7, 6, 12, 0))
        == "2026-07-06T12:00:00Z"
    )
    assert primitives.normalize_optional_datetime(None) is None
    assert primitives.normalize_optional_datetime("2026-07-06T12:00:00+00:00") == (
        "2026-07-06T12:00:00Z"
    )
    with pytest.raises(TypeError, match="datetime-compatible"):
        primitives.normalize_optional_datetime(object())
    assert primitives.normalize_optional_uuid(None) is None
    assert primitives.normalize_optional_uuid(run_id) == str(run_id)
    with pytest.raises(TypeError, match="UUID-compatible"):
        primitives.normalize_optional_uuid(123)


def test_control_plane_primitive_normalizers_cover_nested_containers() -> None:
    payload = _Payload(
        when=datetime(2026, 7, 6, 12, 0, tzinfo=UTC),
        ids=frozenset({2, 1}),
        token=_Token.VALUE,
    )
    normalized = primitives.normalize_canonical_object(payload)
    assert normalized == {
        "ids": [1, 2],
        "token": "token-value",
        "when": "2026-07-06T12:00:00Z",
    }
    assert primitives.normalize_canonical_object(
        {
            "date": date(2026, 7, 6),
            "list": [{"b": 2, "a": 1}, {"a": 1, "b": 3}],
            "tuple": (UUID("00000000-0000-0000-0000-000000000124"),),
            "set": {2, 1},
        }
    ) == {
        "date": "2026-07-06",
        "list": [{"a": 1, "b": 2}, {"a": 1, "b": 3}],
        "set": [1, 2],
        "tuple": ["00000000-0000-0000-0000-000000000124"],
    }


def test_control_plane_metric_and_detail_normalizers_cover_error_edges() -> None:
    assert primitives.normalize_metric_count(True) == 1
    assert primitives.normalize_metric_count(3) == 3
    assert primitives.normalize_metric_count(3.9) == 3
    assert primitives.normalize_metric_count("4") == 4
    with pytest.raises(TypeError, match="Unsupported metric snapshot value"):
        primitives.normalize_metric_count(object())
    assert primitives.normalize_run_ledger_metrics_snapshot(None) is None
    assert primitives.normalize_run_ledger_metrics_snapshot({"b": "2", "a": True}) == {
        "a": 1,
        "b": 2,
    }
    assert primitives.normalize_run_ledger_details(None) is None
    assert primitives.normalize_run_ledger_details({"b": date(2026, 7, 6)}) == {
        "b": "2026-07-06"
    }
