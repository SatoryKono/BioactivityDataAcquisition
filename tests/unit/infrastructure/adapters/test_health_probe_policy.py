"""Unit tests for shared health probe latency policy."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.adapters.health_probe_policy import (
    DEFAULT_SLOW_HEALTH_PROBE_THRESHOLD_SECONDS,
    is_slow_health_probe,
)

pytestmark = pytest.mark.unit


def test_is_slow_health_probe_uses_default_threshold() -> None:
    assert DEFAULT_SLOW_HEALTH_PROBE_THRESHOLD_SECONDS == pytest.approx(5.0)
    assert not is_slow_health_probe(elapsed_seconds=5.0)
    assert is_slow_health_probe(elapsed_seconds=5.01)


def test_is_slow_health_probe_supports_custom_threshold() -> None:
    assert not is_slow_health_probe(elapsed_seconds=1.5, slow_threshold_seconds=2.0)
    assert is_slow_health_probe(elapsed_seconds=2.1, slow_threshold_seconds=2.0)
