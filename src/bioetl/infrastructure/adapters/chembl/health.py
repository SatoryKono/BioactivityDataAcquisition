"""Health check mixin for ChEMBL adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx

from bioetl.domain.exceptions import CriticalError
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.chembl.constants import CHEMBL_STATUS_URL
from bioetl.infrastructure.adapters.http.health import (
    assess_health_from_circuit_breaker,
)

if TYPE_CHECKING:
    from httpx import Response

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

CHEMBL_HEALTH_ERRORS = (
    CriticalError,
    httpx.HTTPError,
    OSError,
    ValueError,
    TypeError,
    RuntimeError,
)


class ChemblHealthMixin:
    """Health-check and adaptive batch-sizing mixin for ChEMBL adapter.

    Determines adapter health from the circuit breaker state machine
    (ADR-007) and adjusts the per-request ``limit`` parameter accordingly
    so that a degraded upstream receives smaller requests.

    Health assessment (delegated to ``assess_health_from_circuit_breaker``):
        * **HEALTHY** -- circuit CLOSED, zero consecutive failures.
        * **DEGRADED** -- circuit CLOSED with >0 failures, or HALF_OPEN.
        * **UNHEALTHY** -- circuit OPEN (failure_threshold reached, default 5).

    Batch-size algorithm (``_get_effective_batch_size``):
        * HEALTHY  -> ``page_size`` (default 1000).
        * DEGRADED -> ``max(100, page_size // 2)``  (halved, floor 100).
        * UNHEALTHY -> raises ``CriticalError`` (fail-fast).

    Active probe (``_probe_health``):
        Hits the ``/chembl/api/data/status`` endpoint. A 200 response with
        ``{"status": "UP"}`` yields HEALTHY; 5xx or transient network errors
        (timeout, connect, read, write) yield DEGRADED; other exceptions
        propagate.
    """

    http_client: UnifiedHTTPClient
    logger: LoggerPort
    provider_name: str
    _page_size: int
    _adapter_metrics: AdapterMetrics

    async def _probe_health(self) -> HealthStatus:
        """Perform ChEMBL-specific health probe."""
        try:
            with self._adapter_metrics.measure_request("/status"):
                response = await self.http_client.get_once(CHEMBL_STATUS_URL)
            return self._handle_health_response(response)
        except CHEMBL_HEALTH_ERRORS as exc:
            status_code = self._extract_http_status_code(exc)
            if status_code is not None and 500 <= status_code < 600:
                self.logger.warning(
                    "health_check_degraded",
                    provider=self.provider_name,
                    reason="status_endpoint_5xx",
                    status_code=status_code,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
                return HealthStatus.DEGRADED
            if isinstance(
                exc,
                (
                    httpx.TimeoutException,
                    httpx.ConnectError,
                    httpx.ReadError,
                    httpx.WriteError,
                ),
            ):
                self.logger.warning(
                    "health_check_degraded",
                    provider=self.provider_name,
                    reason="transient_network_error",
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
                return HealthStatus.DEGRADED
            raise

    def _get_health_status(self) -> HealthStatus:
        """Get health status from circuit breaker state."""
        return assess_health_from_circuit_breaker(self.http_client.circuit_breaker)

    def _get_effective_batch_size(self) -> int:
        """Return the effective ``limit`` parameter for the next API request.

        The value is derived from the circuit breaker state (ADR-007):

        * **HEALTHY** (CLOSED, 0 failures) -- returns ``_page_size`` unchanged
          (default 1000).
        * **DEGRADED** (CLOSED with failures, or HALF_OPEN) -- returns
          ``max(100, _page_size // 2)``.  The floor of 100 prevents
          excessively small requests that would multiply round-trips.
        * **UNHEALTHY** (OPEN) -- raises ``CriticalError`` so the pipeline
          can checkpoint and stop immediately rather than queue doomed
          requests.
        """
        health_status = self._get_health_status()
        failure_count = self.http_client.circuit_breaker.get_failure_count()

        if health_status == HealthStatus.UNHEALTHY:
            raise CriticalError(
                f"ChEMBL adapter is UNHEALTHY after {failure_count} "
                f"consecutive errors (circuit breaker)"
            )
        if health_status == HealthStatus.DEGRADED:
            reduced = max(100, self._page_size // 2)  # Minimum 100
            self.logger.warning(
                "chembl_degraded_mode",
                provider="chembl",
                original_batch_size=self._page_size,
                effective_batch_size=reduced,
                consecutive_errors=failure_count,
            )
            return reduced
        return self._page_size

    def _fallback_health_status(self) -> HealthStatus:
        """Return health status based on circuit breaker state."""
        return self._get_health_status()

    def _get_health_endpoint(self) -> str:
        """Get the health check endpoint for ChEMBL."""
        return "/chembl/api/data/status.json"

    def _handle_health_response(self, response: Response) -> HealthStatus:
        """Process health check response."""
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "UP":
                return HealthStatus.HEALTHY
            else:
                self.logger.warning(
                    "health_check_degraded",
                    provider=self.provider_name,
                    reason="status_not_up",
                    api_status=data.get("status"),
                )
                return HealthStatus.DEGRADED
        else:
            self.logger.warning(
                "health_check_degraded",
                provider=self.provider_name,
                reason="non_200_response",
                status_code=response.status_code,
            )
            return HealthStatus.DEGRADED

    @staticmethod
    def _extract_http_status_code(error: Exception) -> int | None:
        """Extract HTTP status code from exception response if available."""
        response = getattr(error, "response", None)
        if response is None:
            return None
        status_code = getattr(response, "status_code", None)
        return int(status_code) if isinstance(status_code, int) else None

    def get_error_stats(self) -> dict[str, Any]:  # Any: untyped API JSON record
        """Get error statistics from circuit breaker for monitoring.

        Returns:
            Error stats.
        """
        return {
            "circuit_breaker_failures": self.http_client.circuit_breaker.get_failure_count(),
            "circuit_breaker_state": self.http_client.circuit_breaker.get_state().value,
            "health_status": self._get_health_status().value,
        }

    def reset_circuit_breaker(self) -> None:
        """Reset circuit breaker (e.g., after successful recovery)."""
        self.http_client.circuit_breaker.reset()
        self.logger.info("chembl_circuit_breaker_reset", provider="chembl")
