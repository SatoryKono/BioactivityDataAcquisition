"""Active ChEMBL status-endpoint probe helpers."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.chembl.constants import CHEMBL_STATUS_URL

if TYPE_CHECKING:
    from collections.abc import Callable

    from httpx import Response

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

__all__ = [
    "extract_http_status_code",
    "handle_chembl_health_response",
    "probe_chembl_status",
]


def extract_http_status_code(error: Exception) -> int | None:
    """Extract HTTP status code from exception response if available."""
    response = getattr(error, "response", None)
    if response is None:
        return None
    status_code = getattr(response, "status_code", None)
    return int(status_code) if isinstance(status_code, int) else None


def handle_chembl_health_response(
    *,
    response: Response,
    provider_name: str,
    logger: LoggerPort,
) -> HealthStatus:
    """Process health check response from ChEMBL status endpoint."""
    if response.status_code == 200:
        data = response.json()
        if data.get("status") == "UP":
            return HealthStatus.HEALTHY
        logger.warning(
            "health_check_degraded",
            provider=provider_name,
            reason="status_not_up",
            api_status=data.get("status"),
        )
        return HealthStatus.DEGRADED
    logger.warning(
        "health_check_degraded",
        provider=provider_name,
        reason="non_200_response",
        status_code=response.status_code,
    )
    return HealthStatus.DEGRADED


async def probe_chembl_status(
    *,
    http_client: UnifiedHTTPClient,
    adapter_metrics: AdapterMetricsRecorder,
    logger: LoggerPort,
    provider_name: str,
    timeout_seconds: float,
    health_errors: tuple[type[Exception], ...],
    transient_errors: tuple[type[Exception], ...],
    handle_response: Callable[[Response], HealthStatus],
) -> HealthStatus:
    """Perform ChEMBL-specific health probe against the status endpoint."""
    try:
        with adapter_metrics.measure_request("/status"):
            response = await asyncio.wait_for(
                http_client.get_once(CHEMBL_STATUS_URL),
                timeout=timeout_seconds,
            )
        return handle_response(response)
    except health_errors as exc:
        status_code = extract_http_status_code(exc)
        if status_code is not None and 500 <= status_code < 600:
            logger.warning(
                "health_check_degraded",
                provider=provider_name,
                reason="status_endpoint_5xx",
                status_code=status_code,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            return HealthStatus.DEGRADED
        if isinstance(exc, transient_errors):
            logger.warning(
                "health_check_degraded",
                provider=provider_name,
                reason="transient_network_error",
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            return HealthStatus.DEGRADED
        raise
