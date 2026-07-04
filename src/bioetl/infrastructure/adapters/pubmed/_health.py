"""Health and metadata functionality for PubMed adapter.

Part of PubMedAdapter split to comply with LOC limits.
"""

from __future__ import annotations

__all__ = ["PUBMED_HEALTH_ERRORS", "PubMedHealthMixin"]

import time

from bioetl.domain.models.metadata import SourceMetadata
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.common.source_metadata_capability import (
    clear_source_metadata_collector,
    consume_source_metadata,
    get_request_count,
)
from bioetl.infrastructure.adapters.health_probe_policy import (
    is_slow_health_probe,
)
from bioetl.infrastructure.adapters.health_status_policy import (
    classify_health_probe_status,
)
from bioetl.infrastructure.adapters.pubmed._errors import (
    PUBMED_COMMON_ERRORS as PUBMED_HEALTH_ERRORS,
)
from bioetl.infrastructure.adapters.pubmed._state import PubMedAdapterStateMixin

from .constants import ENTREZ_API_BASE


class PubMedHealthMixin(PubMedAdapterStateMixin):
    """Mixin providing health checks and metadata for PubMed."""

    async def _probe_health(self) -> HealthStatus:
        """Perform PubMed-specific health probe.

        Uses einfo.fcgi (database info) instead of esearch.fcgi (search)
        for a lightweight connectivity check without running a query.

        Returns:
            HealthStatus reflecting the current PubMed API availability and response latency.
        """
        try:
            params: dict[str, str] = {
                "db": "pubmed",
                "retmode": "json",
                "email": self.email,
            }
            if self.api_key and "your_" not in self.api_key:
                params["api_key"] = self.api_key

            start_time = time.monotonic()
            with self._adapter_metrics.measure_request("/health"):
                response = await self._http_client.get_once(
                    f"{ENTREZ_API_BASE}einfo.fcgi", params=params
                )
            elapsed = time.monotonic() - start_time

            if response.status_code != 200:
                return classify_health_probe_status(response.status_code)

            if is_slow_health_probe(elapsed_seconds=elapsed):
                self._logger.warning(
                    "pubmed_health_check_slow",
                    elapsed_seconds=round(elapsed, 2),
                )
                return HealthStatus.DEGRADED

            return HealthStatus.HEALTHY
        except PUBMED_HEALTH_ERRORS as e:
            error_type = self._error_handler.get_error_type(e)
            self._logger.warning(
                "health_check_failed",
                provider=self.provider_name,
                error_type=error_type.value,
                error=str(e),
            )
            raise

    def _fallback_health_status(self) -> HealthStatus:
        """Get fallback health status on probe failure.

        Returns:
            HealthStatus.UNHEALTHY as the safe default when health probe cannot execute.
        """
        return HealthStatus.UNHEALTHY

    def _get_health_endpoint(self) -> str:
        """Get the health check endpoint for PubMed.

        Returns:
            Endpoint path string used for PubMed health probe requests.
        """
        return "/entrez/eutils/einfo.fcgi"

    def get_source_metadata(self, api_version: str | None = None) -> SourceMetadata:
        """Get API request metadata and clear collector.

        Args:
            api_version: Api version.

        Returns:
            Source metadata.
        """
        return consume_source_metadata(
            collector=self._request_collector,
            url=ENTREZ_API_BASE,
            api_version=api_version,
        )

    def clear_request_collector(self) -> None:
        """Clear the collector without returning metadata."""
        clear_source_metadata_collector(collector=self._request_collector)

    @property
    def request_count(self) -> int:
        """Number of recorded API requests since last clear."""
        return get_request_count(collector=self._request_collector)
