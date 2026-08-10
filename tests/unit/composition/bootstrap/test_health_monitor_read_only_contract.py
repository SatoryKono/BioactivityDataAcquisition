"""Behavioral contract for the read-only health monitor adapter."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.composition.bootstrap.assembly.health_server import _ReadOnlyHealthMonitor
from bioetl.domain.ports import HealthCheckResult
from bioetl.domain.types import HealthStatus

pytestmark = pytest.mark.unit


def test_read_only_monitor_reports_status_without_retaining_provider_state() -> None:
    """Dashboard-only monitoring maps outcomes while keeping no mutable state."""
    monitor = _ReadOnlyHealthMonitor(metrics=MagicMock())
    result = HealthCheckResult(
        status=HealthStatus.UNHEALTHY,
        latency_ms=12.5,
        provider="chembl",
    )

    assert monitor.update_from_health_check_result(result, logger=object()) is (
        HealthStatus.UNHEALTHY
    )
    assert monitor.record_success("chembl") is HealthStatus.HEALTHY
    assert monitor.record_error("chembl") is HealthStatus.DEGRADED
    assert monitor.get_all_states() == {}
