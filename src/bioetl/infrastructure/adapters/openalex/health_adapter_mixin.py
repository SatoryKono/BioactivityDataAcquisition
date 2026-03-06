"""Health/lifecycle mixin for OpenAlexAdapter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.openalex.health_probe import probe_openalex_health

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


class _OpenAlexHealthHost(Protocol):
    """Structural host contract for OpenAlex health/lifecycle methods."""

    mailto: str
    http_client: UnifiedHTTPClient
    logger: LoggerPort
    _adapter_metrics: AdapterMetrics

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
            api_base="https://api.openalex.org",
            mailto=self.mailto,
            http_client=self.http_client,
            logger=self.logger,
            adapter_metrics=self._adapter_metrics,
            headers=self._build_headers(),
        )

    async def aclose(self: _OpenAlexHealthHost) -> None:
        """Close adapter resources via underlying HTTP client context."""
        if self.http_client:
            await self.http_client.__aexit__(None, None, None)


__all__ = ["OpenAlexAdapterHealthMixin"]
