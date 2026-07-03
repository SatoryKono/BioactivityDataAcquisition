"""Tests for manifest service scaffold time resolution."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from bioetl.application.services.control_plane.manifest.service_scaffold import (
    ManifestServiceScaffoldMixin,
)
from bioetl.domain.context import MISSING_RUNTIME_TIMESTAMP
from tests.helpers.clock import FixedClock


@dataclass(kw_only=True)
class _ManifestScaffoldProbe(ManifestServiceScaffoldMixin):
    created_at_factory: Callable[[], datetime] | None = None


@pytest.mark.unit
def test_resolve_manifest_created_at_prefers_clock() -> None:
    clock_time = datetime(2026, 5, 21, 8, 0, tzinfo=UTC)
    factory_time = datetime(2026, 5, 21, 9, 0, tzinfo=UTC)
    probe = _ManifestScaffoldProbe(
        clock=FixedClock(clock_time),
        created_at_factory=lambda: factory_time,
    )

    assert probe._resolve_created_at() == clock_time


@pytest.mark.unit
def test_resolve_manifest_created_at_uses_factory_without_clock() -> None:
    factory_time = datetime(2026, 5, 21, 9, 0, tzinfo=UTC)
    probe = _ManifestScaffoldProbe(created_at_factory=lambda: factory_time)

    assert probe._resolve_created_at() == factory_time


@pytest.mark.unit
def test_resolve_manifest_created_at_uses_sentinel_without_time_seam() -> None:
    assert _ManifestScaffoldProbe()._resolve_created_at() == MISSING_RUNTIME_TIMESTAMP
