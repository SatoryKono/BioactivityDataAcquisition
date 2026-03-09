"""Health and metadata helpers for SemanticScholarAdapter."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from types import TracebackType
from typing import Literal, Protocol, cast, runtime_checkable

from bioetl.domain.models.metadata import SourceMetadata
from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import HealthStatus, JsonDict
from bioetl.infrastructure.adapters.semanticscholar.constants import (
    SEMANTICSCHOLAR_BASE_URL,
)

__all__ = [
    "SemanticScholarAdapterMetricsProtocol",
    "SemanticScholarHTTPClientProtocol",
    "SemanticScholarHTTPResponseProtocol",
    "SemanticScholarHealthMetadataDependencies",
    "SemanticScholarHealthMetadataMixin",
    "SemanticScholarHealthMetadataMixinABC",
    "SemanticScholarRequestCollectorProtocol",
]


@runtime_checkable
class SemanticScholarHTTPResponseProtocol(Protocol):
    """HTTP response surface required by health checks."""

    status_code: int


@runtime_checkable
class SemanticScholarHTTPClientProtocol(Protocol):
    """HTTP client contract required by SemanticScholarHealthMetadataMixin."""

    async def get_once(
        self,
        url: str,
        params: JsonDict | None = None,
        headers: dict[str, str] | None = None,
    ) -> SemanticScholarHTTPResponseProtocol:
        """Send a single HTTP GET request without retry."""
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        _exc_value: BaseException | None,
        _traceback: TracebackType | None,
    ) -> bool | None: ...


@runtime_checkable
class SemanticScholarAdapterMetricsProtocol(Protocol):
    """Adapter metrics contract required by the health probe."""

    def measure_request(self, endpoint: str) -> AbstractContextManager[None]:
        """Return a context manager that records request duration metrics."""
        ...


@runtime_checkable
class SemanticScholarRequestCollectorProtocol(Protocol):
    """Request-collector contract used by metadata helpers."""

    def to_source_metadata(
        self,
        source_type: Literal["api", "csv", "parquet"] = "api",
        url: str | None = None,
        api_version: str | None = None,
        query_string: str | None = None,
    ) -> SourceMetadata:
        """Build source metadata snapshot from collected request data."""
        ...

    def clear(self) -> None:
        """Reset collected request state."""
        ...

    @property
    def request_count(self) -> int:
        """Return the number of HTTP requests recorded so far."""
        ...


@runtime_checkable
class SemanticScholarHealthMetadataDependencies(Protocol):
    """Host-object dependency contract for SemanticScholarHealthMetadataMixin."""

    http_client: SemanticScholarHTTPClientProtocol
    logger: LoggerPort
    _adapter_metrics: SemanticScholarAdapterMetricsProtocol
    _request_collector: SemanticScholarRequestCollectorProtocol

    def _build_headers(self) -> dict[str, str]: ...


class SemanticScholarHealthMetadataMixinABC(ABC):
    """ABC defining how mixins resolve their dependency contract."""

    @abstractmethod
    def _health_metadata_dependencies(
        self,
    ) -> SemanticScholarHealthMetadataDependencies:
        """Return host dependencies required by health/metadata methods."""
        raise NotImplementedError


_SEMANTICSCHOLAR_HEALTH_ERRORS = (
    OSError,
    ValueError,
    TypeError,
    RuntimeError,
    Exception,
)


class SemanticScholarHealthMetadataMixin(SemanticScholarHealthMetadataMixinABC):
    """Health probe and request-metadata collection methods."""

    def _health_metadata_dependencies(
        self,
    ) -> SemanticScholarHealthMetadataDependencies:
        """Resolve dependency contract from the host adapter instance.

        Returns:
            SemanticScholarHealthMetadataDependencies cast of the current adapter instance.
        """
        return cast("SemanticScholarHealthMetadataDependencies", self)

    async def _probe_health(
        self,
    ) -> HealthStatus:
        """Probe Semantic Scholar health endpoint.

        Returns:
            HealthStatus reflecting the current Semantic Scholar API availability and response latency.
        """
        deps = self._health_metadata_dependencies()
        try:
            url = f"{SEMANTICSCHOLAR_BASE_URL}/paper/search"
            params = {"query": "test", "limit": 1, "fields": "paperId"}

            start_time = time.monotonic()
            with deps._adapter_metrics.measure_request("/health"):
                response = await deps.http_client.get_once(
                    url, params=params, headers=deps._build_headers()
                )
            elapsed = time.monotonic() - start_time

            status_code = response.status_code
            if status_code in (429, 403):
                deps.logger.warning(
                    "semanticscholar_health_check_rate_limited",
                    status_code=status_code,
                    message="Rate limited or forbidden. Consider using API key for stable access.",
                )
                return HealthStatus.DEGRADED

            if status_code != 200:
                deps.logger.warning(
                    "semanticscholar_health_check_failed",
                    status_code=status_code,
                )
                return HealthStatus.UNHEALTHY

            if elapsed > 5.0:
                deps.logger.warning(
                    "semanticscholar_health_check_slow",
                    elapsed_seconds=round(elapsed, 2),
                )
                return HealthStatus.DEGRADED
            return HealthStatus.HEALTHY
        except _SEMANTICSCHOLAR_HEALTH_ERRORS as error:
            error_text = str(error)
            if "429" in error_text or "403" in error_text:
                deps.logger.warning(
                    "semanticscholar_health_check_rate_limited",
                    message="Rate limited or forbidden. Consider using API key.",
                )
                return HealthStatus.DEGRADED
            deps.logger.warning(
                "semanticscholar_health_check_failed",
                error=error_text,
            )
            raise

    def _fallback_health_status(self) -> HealthStatus:
        """Fallback health status when probe fails.

        Returns:
            HealthStatus.UNHEALTHY as the safe default when health probe cannot execute.
        """
        return HealthStatus.UNHEALTHY

    def _get_health_endpoint(self) -> str:
        """Health endpoint path used by probes.

        Returns:
            Endpoint path string used for Semantic Scholar health probe requests.
        """
        return "/paper/search"

    def get_source_metadata(
        self,
        api_version: str | None = None,
    ) -> SourceMetadata:
        """Return and clear request metadata collector state.

        Args:
            api_version: Optional API version string to embed in the metadata.

        Returns:
            SourceMetadata aggregated from all recorded API requests since last clear.
        """
        deps = self._health_metadata_dependencies()
        metadata = deps._request_collector.to_source_metadata(
            source_type="api",
            url=SEMANTICSCHOLAR_BASE_URL,
            api_version=api_version or "v1",
        )
        deps._request_collector.clear()
        return metadata

    def clear_request_collector(self) -> None:
        """Clear request collector without returning metadata."""
        deps = self._health_metadata_dependencies()
        deps._request_collector.clear()

    @property
    def request_count(self) -> int:
        """Recorded API-request count since last clear."""
        deps = self._health_metadata_dependencies()
        return deps._request_collector.request_count

    async def aclose(self) -> None:
        """Close adapter resources."""
        deps = self._health_metadata_dependencies()
        await deps.http_client.__aexit__(None, None, None)
