"""Health and metadata functionality for PubMed adapter.

Part of PubMedAdapter split to comply with LOC limits.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from bioetl.domain.models.metadata import SourceMetadata
from bioetl.domain.types import HealthStatus

if TYPE_CHECKING:
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics
    from bioetl.infrastructure.adapters.common.api_request_collector import APIRequestCollector
    from bioetl.infrastructure.adapters.error_handling import ErrorService

ENTREZ_API_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


class PubMedHealthMixin:
    """Mixin providing health checks and metadata for PubMed."""

    http_client: UnifiedHTTPClient
    logger: LoggerPort
    email: str
    api_key: str | None
    _adapter_metrics: AdapterMetrics
    _request_collector: APIRequestCollector
    provider_name: str
    _error_handler: ErrorService

    async def _probe_health(self) -> HealthStatus:
        """Perform PubMed-specific health probe."""
        try:
            params = {
                "db": "pubmed",
                "term": "health",
                "retmax": "1",
                "retmode": "json",
                "email": self.email,
            }
            if self.api_key and "your_" not in self.api_key:
                params["api_key"] = self.api_key

            start_time = time.monotonic()
            with self._adapter_metrics.measure_request("/health"):
                response = await self.http_client.get_once(
                    f"{ENTREZ_API_BASE}esearch.fcgi", params=params
                )
            elapsed = time.monotonic() - start_time

            if response.status_code != 200:
                self.logger.warning(
                    "pubmed_health_check_failed",
                    status_code=response.status_code,
                )
                return HealthStatus.UNHEALTHY

            if elapsed > 5.0:
                self.logger.warning(
                    "pubmed_health_check_slow",
                    elapsed_seconds=round(elapsed, 2),
                )
                return HealthStatus.DEGRADED

            return HealthStatus.HEALTHY
        except Exception as e:
            error_type = self._error_handler.get_error_type(e)
            self.logger.warning(
                "health_check_failed",
                provider=self.provider_name,
                error_type=error_type.value,
                error=str(e),
            )
            raise

    def _fallback_health_status(self) -> HealthStatus:
        """Get fallback health status on probe failure."""
        return HealthStatus.UNHEALTHY

    def _get_health_endpoint(self) -> str:
        """Get the health check endpoint for PubMed."""
        return "/entrez/eutils/esearch.fcgi"

    def get_source_metadata(self, api_version: str | None = None) -> SourceMetadata:
        """Get API request metadata and clear collector."""
        metadata = self._request_collector.to_source_metadata(
            source_type="api", url=ENTREZ_API_BASE, api_version=api_version
        )
        self._request_collector.clear()
        return metadata

    def clear_request_collector(self) -> None:
        """Clear the collector without returning metadata."""
        self._request_collector.clear()

    @property
    def request_count(self) -> int:
        """Number of recorded API requests since last clear."""
        return self._request_collector.request_count
