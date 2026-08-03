"""Health/lifecycle mixin for OpenAlexAdapter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.openalex._constants import OPENALEX_API_BASE
from bioetl.infrastructure.adapters.openalex.health_probe import probe_openalex_health

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


class _OpenAlexHealthHost(Protocol):
    """Structural host contract for OpenAlex health/lifecycle methods."""

    mailto: str | None
    api_key: str | None
    http_client: UnifiedHTTPClient
    logger: LoggerPort
    _http_client: UnifiedHTTPClient
    _logger: LoggerPort
    _adapter_metrics: AdapterMetricsRecorder

    def _build_headers(self) -> dict[str, str]:
        """Build request headers."""
        ...


class OpenAlexAdapterHealthMixin:
    """Health probe and lifecycle helpers for OpenAlex adapter."""

    async def _probe_health(self: _OpenAlexHealthHost) -> HealthStatus:
        """Probe OpenAlex API health.

        Returns:
            HealthStatus reflecting the current OpenAlex API availability.
        """
        return await probe_openalex_health(
            api_base=OPENALEX_API_BASE,
            mailto=self.mailto,
            api_key=self.api_key,
            http_client=self._http_client,
            logger=self._logger,
            adapter_metrics=self._adapter_metrics,
            headers=self._build_headers(),
        )

    async def aclose(self: _OpenAlexHealthHost) -> None:
        """Close adapter resources via underlying HTTP client context."""
        if self._http_client:
            await self._http_client.__aexit__(None, None, None)


__all__ = ["OpenAlexAdapterHealthMixin"]
