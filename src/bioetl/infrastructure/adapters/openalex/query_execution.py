"""OpenAlex `/works` query execution component."""

from __future__ import annotations

__all__ = ["OpenAlexQueryExecutor"]

import contextlib
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)

if TYPE_CHECKING:
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


@dataclass(slots=True)
class OpenAlexQueryExecutor:
    """Executes OpenAlex `/works` requests with unified telemetry recording."""

    http_client: UnifiedHTTPClient
    adapter_metrics: AdapterMetricsRecorder
    request_collector: APIRequestCollector
    headers_provider: Callable[[], dict[str, str]]
    api_base: str

    async def request_works_payload(self, params: dict[str, str]) -> dict[str, object]:
        """Execute OpenAlex `/works` request and return decoded payload mapping.

        Args:
            params: Query parameters dict to include in the GET request.

        Returns:
            Dictionary containing the decoded JSON payload from the API response.
        """
        url = f"{self.api_base}/works"
        start_time = time.perf_counter()
        with self.adapter_metrics.measure_request("/works"):
            response = await self.http_client.get(
                url,
                params=params,
                headers=self.headers_provider(),
            )

        duration_ms = (time.perf_counter() - start_time) * 1000
        with contextlib.suppress(Exception):
            self.request_collector.record_from_response(response, duration_ms)

        payload = response.json()
        if isinstance(payload, dict):
            return dict(payload)
        return {}
