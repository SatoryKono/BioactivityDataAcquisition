# pyright: reportUninitializedInstanceVariable=false
# pyright: reportAttributeAccessIssue=false
# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Health check mixin for ChEMBL adapter."""

from __future__ import annotations

__all__ = [
    "CHEMBL_HEALTH_ERRORS",
    "CHEMBL_HEALTH_PROBE_TIMEOUT_SECONDS",
    "ChemblHealthMixin",
]


import asyncio
from typing import TYPE_CHECKING

import httpx

from bioetl.domain.exceptions import CriticalError
from bioetl.domain.types import HealthStatus, JsonDict
from bioetl.infrastructure.adapters.chembl.constants import CHEMBL_STATUS_URL
from bioetl.infrastructure.adapters.http.health import (
    assess_health_from_circuit_breaker,
)

if TYPE_CHECKING:
    from httpx import Response

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

from bioetl.infrastructure.adapters.common.error_bundles import (
    build_common_network_error_bundle,
)

CHEMBL_HEALTH_ERRORS = build_common_network_error_bundle(
    CriticalError,
    httpx.HTTPError,
)
CHEMBL_HEALTH_PROBE_TIMEOUT_SECONDS = 5.0
CHEMBL_TRANSIENT_HEALTH_ERRORS = (
    TimeoutError,
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.ReadError,
    httpx.WriteError,
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
        Hits the ``/chembl/api/data/status`` endpoint with a short provider-local
        timeout. A 200 response with ``{"status": "UP"}`` yields HEALTHY; 5xx
        or transient network errors (timeout, connect, read, write) yield
        DEGRADED; other exceptions
        propagate.
    """

    http_client: UnifiedHTTPClient
    logger: LoggerPort
    provider_name: str
    _logger: LoggerPort
    _page_size: int
    _adapter_metrics: AdapterMetricsRecorder
    _last_probe_health_status: HealthStatus | None

    @staticmethod
    def _max_health_status(
        left: HealthStatus,
        right: HealthStatus,
    ) -> HealthStatus:
        """Return the more severe of two health signals."""
        severity = {
            HealthStatus.HEALTHY: 0,
            HealthStatus.DEGRADED: 1,
            HealthStatus.UNHEALTHY: 2,
        }
        return left if severity[left] >= severity[right] else right

    def _get_effective_health_status(self) -> HealthStatus:
        """Combine circuit-breaker and last active probe health.

        The preflight probe can detect an upstream degradation before the
        first fetch attempt mutates the circuit breaker. Preserving the last
        probe result lets the first page fetch react to that signal.
        """
        circuit_status = self._get_health_status()
        probe_status = getattr(self, "_last_probe_health_status", None)
        if probe_status is None:
            return circuit_status
        return self._max_health_status(circuit_status, probe_status)

    def _clear_probe_degraded_state_on_success(self) -> None:
        """Drop stale probe degradation after a successful data request.

        The active `/status` probe is only an early-warning signal. Once a real
        data endpoint request succeeds, retaining a previous probe-only
        DEGRADED state keeps the adapter on a reduced batch size path longer
        than necessary.
        """
        if getattr(self, "_last_probe_health_status", None) == HealthStatus.DEGRADED:
            self._last_probe_health_status = None

    async def _probe_health(self) -> HealthStatus:
        """Perform ChEMBL-specific health probe.

        Returns:
            HealthStatus from the ChEMBL status endpoint or DEGRADED on transient failures.
        """
        try:
            with self._adapter_metrics.measure_request("/status"):
                response = await asyncio.wait_for(
                    self.http_client.get_once(CHEMBL_STATUS_URL),
                    timeout=CHEMBL_HEALTH_PROBE_TIMEOUT_SECONDS,
                )
            status = self._handle_health_response(response)
            self._last_probe_health_status = status
            return status
        except CHEMBL_HEALTH_ERRORS as exc:
            status_code = self._extract_http_status_code(exc)
            if status_code is not None and 500 <= status_code < 600:
                self._last_probe_health_status = HealthStatus.DEGRADED
                self._logger.warning(
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
                CHEMBL_TRANSIENT_HEALTH_ERRORS,
            ):
                self._last_probe_health_status = HealthStatus.DEGRADED
                self._logger.warning(
                    "health_check_degraded",
                    provider=self.provider_name,
                    reason="transient_network_error",
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
                return HealthStatus.DEGRADED
            raise

    def _get_health_status(self) -> HealthStatus:
        """Get health status from circuit breaker state.

        Returns:
            HealthStatus derived from the circuit breaker's current state.
        """
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
        health_status = self._get_effective_health_status()
        failure_count = self.http_client.circuit_breaker.get_failure_count()

        if health_status == HealthStatus.UNHEALTHY:
            raise CriticalError(
                f"ChEMBL adapter is UNHEALTHY after {failure_count} "
                f"consecutive errors (circuit breaker)"
            )
        if health_status == HealthStatus.DEGRADED:
            reduced = max(100, self._page_size // 2)  # Minimum 100
            self._logger.warning(
                "chembl_degraded_mode",
                provider="chembl",
                original_batch_size=self._page_size,
                effective_batch_size=reduced,
                consecutive_errors=failure_count,
            )
            return reduced
        return self._page_size

    def _fallback_health_status(self) -> HealthStatus:
        """Return health status based on circuit breaker state.

        Returns:
            HealthStatus based on the circuit breaker's current state.
        """
        return self._get_health_status()

    def _get_health_endpoint(self) -> str:
        """Get the health check endpoint for ChEMBL.

        Returns:
            Health check endpoint path string for ChEMBL.
        """
        return "/chembl/api/data/status"

    def _handle_health_response(self, response: Response) -> HealthStatus:
        """Process health check response.

        Returns:
            HealthStatus.HEALTHY for a 200 UP response, DEGRADED otherwise.
        """
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "UP":
                return HealthStatus.HEALTHY
            else:
                self._logger.warning(
                    "health_check_degraded",
                    provider=self.provider_name,
                    reason="status_not_up",
                    api_status=data.get("status"),
                )
                return HealthStatus.DEGRADED
        else:
            self._logger.warning(
                "health_check_degraded",
                provider=self.provider_name,
                reason="non_200_response",
                status_code=response.status_code,
            )
            return HealthStatus.DEGRADED

    @staticmethod
    def _extract_http_status_code(error: Exception) -> int | None:
        """Extract HTTP status code from exception response if available.

        Returns:
            HTTP status code as int if present in the exception, None otherwise.
        """
        response = getattr(error, "response", None)
        if response is None:
            return None
        status_code = getattr(response, "status_code", None)
        return int(status_code) if isinstance(status_code, int) else None

    def get_error_stats(self) -> JsonDict:  # Any: untyped API JSON record
        """Get error statistics from circuit breaker for monitoring.

        Returns:
            Error stats.
        """
        return {
            "circuit_breaker_failures": self.http_client.circuit_breaker.get_failure_count(),
            "circuit_breaker_state": self.http_client.circuit_breaker.get_state().value,
            "health_status": self._get_effective_health_status().value,
        }

    def reset_circuit_breaker(self) -> None:
        """Reset circuit breaker (e.g., after successful recovery)."""
        self.http_client.circuit_breaker.reset()
        self._logger.info("chembl_circuit_breaker_reset", provider="chembl")
