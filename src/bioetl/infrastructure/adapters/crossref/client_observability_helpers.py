"""Observability helpers for the CrossRef adapter."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.domain.models.metadata import SourceMetadata
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.common.source_metadata_capability import (
    clear_source_metadata_collector,
    consume_source_metadata,
    get_request_count,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.crossref.query_builder import (
        CrossRefQueryPlanner,
    )
    from bioetl.infrastructure.adapters.crossref.response_mapper import (
        CrossRefResponseMapper,
    )
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


__all__ = [
    "build_crossref_source_metadata",
    "clear_crossref_request_collector",
    "get_crossref_request_count",
    "probe_crossref_health",
]


async def probe_crossref_health(
    *,
    http_client: UnifiedHTTPClient,
    query_builder: CrossRefQueryPlanner,
    response_mapper: CrossRefResponseMapper,
    adapter_metrics: AdapterMetricsRecorder,
    headers_provider: Callable[[], dict[str, str]],
    logger: LoggerPort,
    health_errors: tuple[type[Exception], ...],
) -> HealthStatus:
    """Probe CrossRef health and return the classified adapter status."""
    try:
        url = query_builder.build_health_probe_url()
        params = query_builder.build_health_probe_params()

        start_time = time.monotonic()
        with adapter_metrics.measure_request("/health"):
            response = await http_client.get_once(
                url,
                params=params,
                headers=headers_provider(),
            )
        elapsed = time.monotonic() - start_time

        probe_mapping = response_mapper.map_health_probe(
            status_code=response.status_code,
            elapsed_seconds=elapsed,
        )
        if probe_mapping.event_name == "crossref_health_check_slow":
            logger.warning(
                probe_mapping.event_name,
                elapsed_seconds=round(elapsed, 2),
            )
        elif probe_mapping.event_name is not None:
            logger.warning(
                probe_mapping.event_name,
                status_code=response.status_code,
                classified_status=probe_mapping.status.value,
            )
        return probe_mapping.status
    except health_errors as error:
        logger.warning(
            "crossref_health_check_failed",
            error=str(error),
        )
        raise


def build_crossref_source_metadata(
    *,
    request_collector: APIRequestCollector,
    api_base: str,
    api_version: str | None = None,
) -> SourceMetadata:
    """Build and consume aggregated CrossRef request metadata."""
    return consume_source_metadata(
        collector=request_collector,
        url=api_base,
        api_version=api_version,
    )


def clear_crossref_request_collector(
    *,
    request_collector: APIRequestCollector,
) -> None:
    """Clear CrossRef request collector state."""
    clear_source_metadata_collector(collector=request_collector)


def get_crossref_request_count(
    *,
    request_collector: APIRequestCollector,
) -> int:
    """Return the current CrossRef request count."""
    return get_request_count(collector=request_collector)
