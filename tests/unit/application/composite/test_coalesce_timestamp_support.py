"""Unit tests for composite timestamp coalesce helpers (ARCH-REF-06)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.application.composite._coalesce_timestamp_support import (
    count_timestamp_companions,
    resolve_timestamp_companion,
    should_replace_latest_candidate,
    timestamp_sort_key,
)

pytestmark = pytest.mark.unit


def test_resolve_timestamp_companion_finds_updated_at() -> None:
    assert (
        resolve_timestamp_companion(
            "chembl.activity.value",
            {"chembl.activity.value", "chembl.activity.updated_at"},
        )
        == "chembl.activity.updated_at"
    )


def test_timestamp_sort_key_orders_datetime_above_string() -> None:
    dt = datetime(2026, 1, 1, tzinfo=UTC)
    assert timestamp_sort_key(dt)[0] > timestamp_sort_key("2026-01-01")[0]


def test_should_replace_prefers_newer_timestamp() -> None:
    assert should_replace_latest_candidate(
        current_timestamp_key=(3, 100.0),
        rank=1,
        best_timestamp_key=(3, 50.0),
        best_rank=0,
    )


def test_count_timestamp_companions() -> None:
    assert count_timestamp_companions({"a": "t1", "b": None, "c": "t2"}) == 2
