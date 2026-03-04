# mypy: disable-error-code=no-any-return
"""Health and metadata helpers for SemanticScholarAdapter."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from bioetl.domain.models.metadata import SourceMetadata
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.semanticscholar.constants import (
    SEMANTICSCHOLAR_BASE_URL,
)

if TYPE_CHECKING:
    pass


_SEMANTICSCHOLAR_HEALTH_ERRORS = (
    OSError,
    ValueError,
    TypeError,
    RuntimeError,
    Exception,
)


class SemanticScholarHealthMetadataMixin:
    """Health probe and request-metadata collection methods."""

    async def _probe_health(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
    ) -> (
        HealthStatus
    ):  # Any: mixin self type is provided structurally by composed adapter class
        """Probe Semantic Scholar health endpoint."""
        try:
            url = f"{SEMANTICSCHOLAR_BASE_URL}/paper/search"
            params = {"query": "test", "limit": 1, "fields": "paperId"}

            start_time = time.monotonic()
            with self._adapter_metrics.measure_request("/health"):
                response = await self.http_client.get_once(
                    url, params=params, headers=self._build_headers()
                )
            elapsed = time.monotonic() - start_time

            if response.status_code in (429, 403):
                self.logger.warning(
                    "semanticscholar_health_check_rate_limited",
                    status_code=response.status_code,
                    message="Rate limited or forbidden. Consider using API key for stable access.",
                )
                return HealthStatus.DEGRADED

            if response.status_code != 200:
                self.logger.warning(
                    "semanticscholar_health_check_failed",
                    status_code=response.status_code,
                )
                return HealthStatus.UNHEALTHY

            if elapsed > 5.0:
                self.logger.warning(
                    "semanticscholar_health_check_slow",
                    elapsed_seconds=round(elapsed, 2),
                )
                return HealthStatus.DEGRADED
            return HealthStatus.HEALTHY
        except _SEMANTICSCHOLAR_HEALTH_ERRORS as error:
            error_text = str(error)
            if "429" in error_text or "403" in error_text:
                self.logger.warning(
                    "semanticscholar_health_check_rate_limited",
                    message="Rate limited or forbidden. Consider using API key.",
                )
                return HealthStatus.DEGRADED
            self.logger.warning(
                "semanticscholar_health_check_failed",
                error=error_text,
            )
            raise

    def _fallback_health_status(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
    ) -> (
        HealthStatus
    ):  # Any: mixin self type is provided structurally by composed adapter class
        """Fallback health status when probe fails."""
        return HealthStatus.UNHEALTHY

    def _get_health_endpoint(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
    ) -> str:  # Any: mixin self type is provided structurally by composed adapter class
        """Health endpoint path used by probes."""
        return "/paper/search"

    def get_source_metadata(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
        api_version: str
        | None = None,  # Any: mixin self type is provided structurally by composed adapter class
    ) -> SourceMetadata:
        """Return and clear request metadata collector state."""
        metadata = self._request_collector.to_source_metadata(
            source_type="api",
            url=SEMANTICSCHOLAR_BASE_URL,
            api_version=api_version or "v1",
        )
        self._request_collector.clear()
        return metadata

    def clear_request_collector(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
    ) -> (
        None
    ):  # Any: mixin self type is provided structurally by composed adapter class
        """Clear request collector without returning metadata."""
        self._request_collector.clear()

    @property
    def request_count(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
    ) -> int:  # Any: mixin self type is provided structurally by composed adapter class
        """Recorded API-request count since last clear."""
        return self._request_collector.request_count

    async def aclose(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
    ) -> (
        None
    ):  # Any: mixin self type is provided structurally by composed adapter class
        """Close adapter resources."""
        if self.http_client:
            await self.http_client.__aexit__(None, None, None)
