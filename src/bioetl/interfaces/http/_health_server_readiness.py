"""Readiness payload construction for HealthServer."""

from __future__ import annotations

import asyncio
from typing import Protocol

from bioetl.application.observability.current_metrics_reconciliation import (
    current_metrics_reconciliation_check,
)
from bioetl.domain.types import JsonDict
from bioetl.interfaces.http.report_root_config import (
    enforce_report_root_marker,
    report_root_readiness_check,
)
from bioetl.interfaces.http.types import HealthResponse


class _ReadinessHost(Protocol):
    _health_monitor: object | None
    _metrics_exposition: object

    def _response_timestamp(self) -> str: ...
    def _get_provider_statuses(self) -> dict[str, JsonDict]: ...


async def build_readiness_response(host: _ReadinessHost) -> HealthResponse:
    """Build /health/ready payload, offloading report-root filesystem I/O."""
    report_root_check = await asyncio.to_thread(report_root_readiness_check)
    checks: JsonDict = {
        "report_root": report_root_check,
        "current_metrics": current_metrics_reconciliation_check(
            exposition=host._metrics_exposition.build_exposition()
        ),
    }
    status = "healthy"
    if (
        enforce_report_root_marker()
        and report_root_check.get("status") != "healthy"
    ):
        status = "unhealthy"
    if not host._health_monitor:
        checks["message"] = "No health monitor configured"
        return HealthResponse(
            status=status,
            timestamp=host._response_timestamp(),
            checks=checks,
        )
    provider_statuses = host._get_provider_statuses()
    checks["providers"] = provider_statuses
    has_unhealthy = any(
        item.get("status") == "unhealthy" for item in provider_statuses.values()
    )
    if has_unhealthy:
        status = "unhealthy"
    return HealthResponse(
        status=status,
        timestamp=host._response_timestamp(),
        checks=checks,
    )
