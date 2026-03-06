"""OpenAlex health probe component."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.health_status_policy import (
    classify_health_probe_status,
)
from bioetl.infrastructure.adapters.openalex.query_builder import (
    build_openalex_health_probe_params,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


async def probe_openalex_health(
    *,
    api_base: str,
    mailto: str,
    http_client: UnifiedHTTPClient,
    logger: LoggerPort,
    adapter_metrics: AdapterMetrics,
    headers: dict[str, str],
) -> HealthStatus:
    """Probe OpenAlex API health with latency-based degradation threshold."""
    url = f"{api_base}/works"
    params = build_openalex_health_probe_params(mailto)

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

    if elapsed > 5.0:
        logger.warning(
            "openalex_health_check_slow",
            elapsed_seconds=round(elapsed, 2),
        )
        return HealthStatus.DEGRADED

    return HealthStatus.HEALTHY


__all__ = ["probe_openalex_health"]
