"""Health endpoint helpers for UniProt ID mapping client."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, cast, runtime_checkable

from bioetl.domain.types import HealthStatus

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


@runtime_checkable
class IDMappingHealthDependencies(Protocol):
    """Host dependency contract for IDMappingHealthMixin."""

    provider_name: str
    logger: LoggerPort
    http_client: UnifiedHTTPClient
    _adapter_metrics: AdapterMetricsRecorder
    base_url: str


class IDMappingHealthMixin:
    """Health check behavior isolated from mapping transport logic."""

    provider_name: str
    logger: LoggerPort
    http_client: UnifiedHTTPClient
    _adapter_metrics: AdapterMetricsRecorder
    base_url: str

    def _health_deps(self) -> IDMappingHealthDependencies:
        """Return typed dependency view of the host client.

        Returns:
            IDMappingHealthDependencies cast of the current client instance.
        """
        return cast("IDMappingHealthDependencies", self)

    async def _probe_health(self) -> HealthStatus:
        """Perform health probe for ID Mapping API.

        Returns:
            HealthStatus reflecting the current UniProt ID Mapping API availability.
        """
        deps = self._health_deps()
        url = f"{deps.base_url}/configure/idmapping/fields"
        with deps._adapter_metrics.measure_request("/health"):
            response = await deps.http_client.get_once(url, params=None)

        if response.status_code != 200:
            deps.logger.warning(
                "health_check_degraded",
                provider=deps.provider_name,
                reason="non_200_response",
                status_code=response.status_code,
            )
            return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    def _get_health_endpoint(self) -> str:
        """Get health check endpoint for ID Mapping API.

        Returns:
            Endpoint path string used for UniProt ID Mapping health probe requests.
        """
        return "/configure/idmapping/fields"
