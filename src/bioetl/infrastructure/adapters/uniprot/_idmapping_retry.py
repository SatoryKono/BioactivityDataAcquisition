"""Polling/retry logic for UniProt ID mapping jobs."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Protocol, cast, runtime_checkable

from bioetl.infrastructure.adapters.uniprot._idmapping_errors import (
    IDMappingJobError,
    IDMappingTimeoutError,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


@runtime_checkable
class IDMappingRetryDependencies(Protocol):
    """Host dependency contract for IDMappingRetryMixin."""

    logger: LoggerPort
    http_client: UnifiedHTTPClient
    _adapter_metrics: AdapterMetricsRecorder
    POLLING_INTERVAL: float
    MAX_POLL_ATTEMPTS: int
    base_url: str


class IDMappingRetryMixin:
    """Retry and polling behavior for async job completion."""

    logger: LoggerPort
    http_client: UnifiedHTTPClient
    _adapter_metrics: AdapterMetricsRecorder
    POLLING_INTERVAL: float
    MAX_POLL_ATTEMPTS: int
    base_url: str

    def _retry_deps(self) -> IDMappingRetryDependencies:
        """Return typed dependency view of the host client.

        Returns:
            IDMappingRetryDependencies cast of the current client instance.
        """
        return cast("IDMappingRetryDependencies", self)

    async def _poll_until_ready(self, job_id: str) -> str | None:
        """Poll job status until complete.

        Returns:
            Results URL string if available from redirect, None if polling succeeded without redirect.
        """
        deps = self._retry_deps()
        url = f"{deps.base_url}/idmapping/status/{job_id}"

        for attempt in range(deps.MAX_POLL_ATTEMPTS):
            with deps._adapter_metrics.measure_request("/idmapping/status"):
                response = await deps.http_client.get(url)

            response_url = str(response.url) if hasattr(response, "url") else ""
            if "/results/" in response_url or "/uniprotkb/results/" in response_url:
                deps.logger.debug(
                    "idmapping_job_finished",
                    job_id=job_id,
                    attempts=attempt + 1,
                    detected_by="redirect_to_results",
                    results_url=response_url,
                )
                return response_url

            if response.status_code not in (200, 303):
                deps.logger.warning(
                    "idmapping_status_error",
                    job_id=job_id,
                    status_code=response.status_code,
                )
                await asyncio.sleep(deps.POLLING_INTERVAL)
                continue

            result = response.json()
            if "results" in result:
                deps.logger.debug(
                    "idmapping_job_finished",
                    job_id=job_id,
                    attempts=attempt + 1,
                    detected_by="results_in_response",
                )
                return response_url or None

            status = result.get("jobStatus", "UNKNOWN")
            if response.status_code == 303:
                status = "FINISHED"

            if status == "FINISHED":
                deps.logger.debug(
                    "idmapping_job_finished",
                    job_id=job_id,
                    attempts=attempt + 1,
                    detected_by="job_status",
                )
                return None

            if status == "ERROR":
                error_msg = result.get("errorMessage", "Unknown error")
                deps.logger.error(
                    "idmapping_job_error",
                    job_id=job_id,
                    error=error_msg,
                )
                raise IDMappingJobError(job_id=job_id, message=error_msg)

            await asyncio.sleep(deps.POLLING_INTERVAL)

        raise IDMappingTimeoutError(job_id=job_id, attempts=deps.MAX_POLL_ATTEMPTS)
