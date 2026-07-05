"""Tests for stable lineage fragment ID helpers."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.application.services.lineage import (
    metadata_lineage_fragment_ids as fragment_ids,
)

pytestmark = pytest.mark.unit


def test_fragment_timestamp_uses_first_supplied_timestamp() -> None:
    first = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    second = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)

    assert fragment_ids.fragment_timestamp(None, first, second) == first


def test_fragment_timestamp_falls_back_to_current_time(monkeypatch) -> None:
    now = datetime(2026, 1, 3, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(fragment_ids, "current_utc_time", lambda: now)

    assert fragment_ids.fragment_timestamp(None, None) == now
