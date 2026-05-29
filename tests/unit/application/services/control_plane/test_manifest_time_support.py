"""Tests for shared control-plane manifest time helpers."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.application.services.control_plane.manifest_time_support import (
    resolve_manifest_created_at,
)
from bioetl.domain.context import MISSING_RUNTIME_TIMESTAMP
from tests.helpers.clock import FixedClock


@pytest.mark.unit
def test_resolve_manifest_created_at_prefers_clock() -> None:
    clock_time = datetime(2026, 5, 21, 8, 0, tzinfo=UTC)
    factory_time = datetime(2026, 5, 21, 9, 0, tzinfo=UTC)

    assert (
        resolve_manifest_created_at(
            clock=FixedClock(clock_time),
            created_at_factory=lambda: factory_time,
        )
        == clock_time
    )


@pytest.mark.unit
def test_resolve_manifest_created_at_uses_factory_without_clock() -> None:
    factory_time = datetime(2026, 5, 21, 9, 0, tzinfo=UTC)

    assert (
        resolve_manifest_created_at(
            clock=None,
            created_at_factory=lambda: factory_time,
        )
        == factory_time
    )


@pytest.mark.unit
def test_resolve_manifest_created_at_uses_sentinel_without_time_seam() -> None:
    assert (
        resolve_manifest_created_at(clock=None, created_at_factory=None)
        == MISSING_RUNTIME_TIMESTAMP
    )
