"""UniProt health probe component."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.uniprot.query_builder import (
    build_uniprot_health_probe_params,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


async def probe_uniprot_health(
    *,
    base_url: str,
    provider_name: str,
    http_client: UnifiedHTTPClient,
    logger: LoggerPort,
    adapter_metrics: AdapterMetricsRecorder,
    healthy_status_provider: Callable[[], HealthStatus],
) -> HealthStatus:
    """Probe UniProt API health endpoint.

    Returns:
        HealthStatus reflecting the current UniProt API availability and response status.
    """
    params = build_uniprot_health_probe_params()
    try:
        with adapter_metrics.measure_request("/health"):
            response = await http_client.get_once(
                f"{base_url}/uniprotkb/search", params=params
            )
    except Exception as exc:
        # Health probes must not raise: transport, status, or unexpected
        # connection failures degrade status for operators.
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        logger.warning(
            "health_check_degraded",
            provider=provider_name,
            reason="request_error",
            status_code=status_code,
            error_type=type(exc).__name__,
        )
        return HealthStatus.DEGRADED

    if response.status_code != 200:
        logger.warning(
            "health_check_degraded",
            provider=provider_name,
            reason="non_200_response",
            status_code=response.status_code,
        )
        return HealthStatus.DEGRADED

    return healthy_status_provider()


__all__ = ["probe_uniprot_health"]
