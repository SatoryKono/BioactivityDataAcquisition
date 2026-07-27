"""Branch coverage for domain HealthCheckResult (TD-R-02 / #6678)."""

from __future__ import annotations

pytestmark = pytest.mark.unit


from datetime import UTC, datetime

from bioetl.domain.ports.health_check import HealthCheckResult
from bioetl.domain.types import HealthStatus


def test_health_check_result_status_flags_and_exports() -> None:
    checked_at = datetime(2026, 7, 27, tzinfo=UTC)
    healthy = HealthCheckResult(
        status=HealthStatus.HEALTHY,
        latency_ms=12.5,
        provider="chembl",
        endpoint="/status",
        checked_at=checked_at,
    )
    assert healthy.is_healthy is True
    assert healthy.is_degraded is False
    assert healthy.is_unhealthy is False
    assert healthy.to_metric_labels() == {"provider": "chembl", "status": "healthy"}
    payload = healthy.to_dict()
    assert payload["status"] == HealthStatus.HEALTHY.value
    assert payload["checked_at"] == checked_at.isoformat()

    degraded = HealthCheckResult(
        status=HealthStatus.DEGRADED,
        latency_ms=90.0,
        provider="pubchem",
        last_error="slow",
        consecutive_failures=2,
    )
    assert degraded.is_degraded is True
    assert degraded.to_dict()["checked_at"] is None

    unhealthy = HealthCheckResult(
        status=HealthStatus.UNHEALTHY,
        latency_ms=0.0,
        provider="uniprot",
    )
    assert unhealthy.is_unhealthy is True
