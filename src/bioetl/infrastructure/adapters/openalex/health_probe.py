"""OpenAlex health probe component."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.health_probe_policy import (
    is_slow_health_probe,
)
from bioetl.infrastructure.adapters.health_status_policy import (
    classify_health_probe_status,
)
from bioetl.infrastructure.adapters.openalex.query_builder import (
    build_openalex_health_probe_params,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


async def probe_openalex_health(
    *,
    api_base: str,
    mailto: str | None,
    api_key: str | None,
    http_client: UnifiedHTTPClient,
    logger: LoggerPort,
    adapter_metrics: AdapterMetricsRecorder,
    headers: dict[str, str],
) -> HealthStatus:
    """Probe OpenAlex API health with latency-based degradation threshold.

    Args:
        api_base: Base URL for the OpenAlex API (e.g., "https://api.openalex.org").
        mailto: Optional email address retained for legacy request attribution.
        api_key: Optional OpenAlex API key.
        http_client: HTTP client for making the probe request.
        logger: Logger port for structured warning output.
        adapter_metrics: Adapter metrics for measuring request latency.
        headers: Request headers to include in the probe request.

    Returns:
        HealthStatus reflecting the current OpenAlex API availability and response latency.
    """
    url = f"{api_base}/works"
    params = build_openalex_health_probe_params(mailto, api_key=api_key)

    start_time = time.monotonic()
    with adapter_metrics.measure_request("/health"):
        response = await http_client.get_once(url, params=params, headers=headers)
    elapsed = time.monotonic() - start_time

    if response.status_code != 200:
        status = classify_health_probe_status(response.status_code)
        logger.warning(
            (
                "openalex_health_check_degraded"
                if status == HealthStatus.DEGRADED
                else "openalex_health_check_failed"
            ),
            status_code=response.status_code,
            classified_status=status.value,
        )
        return status

    if is_slow_health_probe(elapsed_seconds=elapsed):
        logger.warning(
            "openalex_health_check_slow",
            elapsed_seconds=round(elapsed, 2),
        )
        return HealthStatus.DEGRADED

    return HealthStatus.HEALTHY


__all__ = ["probe_openalex_health"]
