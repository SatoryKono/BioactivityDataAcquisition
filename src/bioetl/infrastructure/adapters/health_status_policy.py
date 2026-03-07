"""Shared health probe status classification policy."""

from __future__ import annotations

from bioetl.domain.types import HealthStatus

TRANSIENT_DEGRADED_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})
AUTH_FAILURE_STATUS_CODES = frozenset({401, 403})


def classify_health_probe_status(status_code: int) -> HealthStatus:
    """Classify non-200 health probe status into DEGRADED/UNHEALTHY.

    Args:
        status_code: HTTP status code from the health probe response.

    Returns:
        HealthStatus.DEGRADED for transient errors, HealthStatus.UNHEALTHY otherwise.
    """
    if status_code in TRANSIENT_DEGRADED_STATUS_CODES:
        return HealthStatus.DEGRADED
    if status_code in AUTH_FAILURE_STATUS_CODES:
        return HealthStatus.UNHEALTHY
    return HealthStatus.UNHEALTHY


__all__ = [
    "AUTH_FAILURE_STATUS_CODES",
    "TRANSIENT_DEGRADED_STATUS_CODES",
    "classify_health_probe_status",
]
