# Host/cast bridge residual; prefer Protocol self when rewriting module.
"""Polling/retry logic for UniProt ID mapping jobs."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Protocol, cast, runtime_checkable

from bioetl.infrastructure.adapters.uniprot._idmapping_errors import (
    IDMappingJobError,
    IDMappingTimeoutError,
)
from bioetl.infrastructure.adapters.uniprot._idmapping_url_policy import (
    trusted_idmapping_url,
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
    """Retry and polling behavior for async job completion.

    Host attributes / class constants come from the concrete client; not
    re-declared here so MRO types stay compatible with BaseHttpAdapter.
    """

    def _retry_deps(self) -> IDMappingRetryDependencies:
        """Return typed dependency view of the host client.

        Returns:
            IDMappingRetryDependencies cast of the current client instance.
        """
        return cast("IDMappingRetryDependencies", self)  # pyright: ignore[reportInvalidCast]

    @staticmethod
    def _check_redirect_to_results(response: object, *, base_url: str) -> str | None:
        """Return results URL if response redirected to a results endpoint."""
        response_url = str(response.url) if hasattr(response, "url") else ""  # pyright: ignore[reportAttributeAccessIssue]
        if "/results/" in response_url or "/uniprotkb/results/" in response_url:
            return trusted_idmapping_url(base_url, response_url)
        return None

    @staticmethod
    def _resolve_job_status(response: object, result: dict[str, object]) -> str:
        """Determine effective job status from response code and payload."""
        if "results" in result:
            return "HAS_RESULTS"
        if getattr(response, "status_code", 0) == 303:
            return "FINISHED"
        return str(result.get("jobStatus", "UNKNOWN"))

    @staticmethod
    def _completed_poll_result(
        deps: IDMappingRetryDependencies,
        *,
        response: object,
        result: dict[str, object],
        status: str,
        job_id: str,
        attempt: int,
    ) -> tuple[bool, str | None]:
        """Handle terminal polling states and return completion plus URL."""
        if status == "HAS_RESULTS":
            deps.logger.debug(
                "idmapping_job_finished",
                job_id=job_id,
                attempts=attempt + 1,
                detected_by="results_in_response",
            )
            response_url = (
                str(response.url) if hasattr(response, "url") else ""  # pyright: ignore[reportAttributeAccessIssue]
            )
            return (
                True,
                trusted_idmapping_url(deps.base_url, response_url)
                if response_url
                else None,
            )
        if status == "FINISHED":
            deps.logger.debug(
                "idmapping_job_finished",
                job_id=job_id,
                attempts=attempt + 1,
                detected_by="job_status",
            )
            return True, None
        if status == "ERROR":
            error_msg = str(result.get("errorMessage", "Unknown error"))
            deps.logger.error(
                "idmapping_job_error",
                job_id=job_id,
                error=error_msg,
            )
            raise IDMappingJobError(job_id=job_id, message=error_msg)
        return False, None

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

            redirect_url = self._check_redirect_to_results(
                response, base_url=deps.base_url
            )
            if redirect_url is not None:
                deps.logger.debug(
                    "idmapping_job_finished",
                    job_id=job_id,
                    attempts=attempt + 1,
                    detected_by="redirect_to_results",
                    results_url=redirect_url,
                )
                return redirect_url

            if response.status_code not in (200, 303):
                deps.logger.warning(
                    "idmapping_status_error",
                    job_id=job_id,
                    status_code=response.status_code,
                )
                await asyncio.sleep(deps.POLLING_INTERVAL)
                continue

            raw_payload = response.json()
            if not isinstance(raw_payload, dict):
                deps.logger.warning(
                    "idmapping_status_invalid_payload",
                    job_id=job_id,
                    status_code=response.status_code,
                    payload_type=type(raw_payload).__name__,
                )
                await asyncio.sleep(deps.POLLING_INTERVAL)
                continue
            result: dict[str, object] = raw_payload
            status = self._resolve_job_status(response, result)
            completed, result_url = self._completed_poll_result(
                deps,
                response=response,
                result=result,
                status=status,
                job_id=job_id,
                attempt=attempt,
            )
            if completed:
                return result_url

            await asyncio.sleep(deps.POLLING_INTERVAL)

        raise IDMappingTimeoutError(job_id=job_id, attempts=deps.MAX_POLL_ATTEMPTS)
