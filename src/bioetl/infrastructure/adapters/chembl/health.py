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


class ChemblHealthMixin:
    """Mixin for health-related logic in ChEMBL adapter."""

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
        except Exception as exc:
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
        """Get batch size adjusted for health: full if HEALTHY, half if DEGRADED."""
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

    def get_error_stats(self) -> dict[str, Any]:
        """Get error statistics from circuit breaker for monitoring."""
        return {
            "circuit_breaker_failures": self.http_client.circuit_breaker.get_failure_count(),
            "circuit_breaker_state": self.http_client.circuit_breaker.get_state().value,
            "health_status": self._get_health_status().value,
        }

    def reset_circuit_breaker(self) -> None:
        """Reset circuit breaker (e.g., after successful recovery)."""
        self.http_client.circuit_breaker.reset()
        self.logger.info("chembl_circuit_breaker_reset", provider="chembl")
