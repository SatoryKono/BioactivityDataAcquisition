"""Health check service for administrative operations (Application layer).

Provides high-level health check operations for CLI and other interfaces.
Abstracts provider health checking behind application service.

Implements RULES.md §1.1 - Application layer depends only on Domain.
"""

from __future__ import annotations

__all__ = [
    "DataSourceFactoryPort",
    "HealthCheckSummary",
    "HealthResult",
    "HealthService",
]


from dataclasses import dataclass
from datetime import datetime
from typing import cast, Any, TYPE_CHECKING

from bioetl.domain.exceptions import BioETLError, NetworkError
from bioetl.domain.ports import (
    ClockPort,
    DataSourceFactoryPort,
    HealthCheckPort,
    HealthCheckResult,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import JsonDict

_HEALTH_SERVICE_ERRORS = (
    NetworkError,
    BioETLError,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
)


@dataclass(frozen=True, slots=True)
class HealthResult:
    """Result of a health check for a single provider.

    Attributes:
        provider: Name of the provider.
        status: Health status (healthy, degraded, unhealthy, unknown).
        latency_ms: Latency of the health check in milliseconds.
        endpoint: The endpoint used for health check.
        error: Error message if health check failed.
        checked_at: Timestamp when the health check was performed.
    """

    provider: str
    status: str
    latency_ms: float | None = None
    endpoint: str | None = None
    error: str | None = None
    checked_at: datetime | None = None

    @property
    def is_healthy(self) -> bool:
        """Return True if status is healthy."""
        return self.status == "healthy"

    @property
    def is_degraded(self) -> bool:
        """Return True if status is degraded."""
        return self.status == "degraded"

    @property
    def is_unhealthy(self) -> bool:
        """Return True if status is unhealthy or unknown."""
        return self.status in ("unhealthy", "unknown")

    def to_dict(self) -> JsonDict:  # Any: heterogeneous health metric values
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation.
        """
        result: JsonDict = {  # Any: heterogeneous health metric values
            "status": self.status,
        }
        if self.latency_ms is not None:
            result["latency_ms"] = f"{self.latency_ms:.2f}"
        if self.endpoint:
            result["endpoint"] = self.endpoint
        if self.error:
            result["error"] = self.error
        return result


@dataclass(frozen=True, slots=True)
class HealthCheckSummary:
    """Summary of health check results across all providers.

    Attributes:
        results: Dictionary mapping provider names to health results.
        all_healthy: True if all providers are healthy.
        checked_at: Timestamp when the health checks were performed.
    """

    results: dict[str, HealthResult]
    all_healthy: bool
    checked_at: datetime | None = None

    @property
    def healthy_count(self) -> int:
        """Number of healthy providers."""
        return sum(1 for r in self.results.values() if r.is_healthy)

    @property
    def unhealthy_count(self) -> int:
        """Number of unhealthy providers."""
        return sum(1 for r in self.results.values() if r.is_unhealthy)

    def to_dict(self) -> dict[str, JsonDict]:  # Any: heterogeneous health m...
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation.
        """
        return {name: result.to_dict() for name, result in self.results.items()}


@dataclass
class HealthService:
    """Service for provider health check operations.

    Provides high-level operations for checking provider health
    used by CLI and other interfaces. Abstracts data source factory
    for Application-layer abstraction.

    Attributes:
        logger: Structured logger for observability.
        _factory: Data source factory for creating adapters.

    Example:
        >>> service = HealthService(logger=logger, _factory=DataSourceFactory)
        >>> summary = await service.check_providers()
        >>> if summary.all_healthy:
        ...     logger.info("All providers healthy")
    """

    logger: LoggerPort
    _factory: DataSourceFactoryPort
    clock: ClockPort

    async def check_providers(
        self,
        providers: list[str] | None = None,
    ) -> HealthCheckSummary:
        """Check health of data providers.

        Args:
            providers: Specific providers to check. If None, checks all available.

        Returns:
            HealthCheckSummary with results for all checked providers.
        """
        self.logger.debug("Starting health checks", providers=providers)

        # Get providers to check
        available_providers = self._factory.list_providers()
        providers_to_check = list(providers) if providers else available_providers

        results: dict[str, HealthResult] = {}

        for provider in providers_to_check:
            result = await self._check_single_provider(provider)
            results[provider] = result

        all_healthy = all(r.is_healthy for r in results.values())

        summary = HealthCheckSummary(
            results=results,
            all_healthy=all_healthy,
            checked_at=self.clock.now(),
        )

        self.logger.info(
            "Health checks completed",
            providers_checked=len(results),
            all_healthy=all_healthy,
            healthy_count=summary.healthy_count,
            unhealthy_count=summary.unhealthy_count,
        )

        return summary

    async def _check_single_provider(self, provider: str) -> HealthResult:
        """Check health of a single provider.

        Args:
            provider: Name of the provider to check.

        Returns:
            HealthResult for the provider.
        """
        self.logger.debug("Checking provider health", provider=provider)

        try:
            adapter = self._factory.create(provider)

            # Use runtime checkable protocol to verify adapter implements HealthCheckPort
            if isinstance(adapter, HealthCheckPort):
                result: HealthCheckResult = await self._run_adapter_health_check(
                    adapter
                )
                return HealthResult(
                    provider=provider,
                    status=result.status.value.lower(),
                    latency_ms=result.latency_ms,
                    endpoint=result.endpoint,
                    error=result.last_error,
                    checked_at=result.checked_at or self.clock.now(),
                )

            # Adapter doesn't implement HealthCheckPort
            self.logger.warning(
                "Adapter does not implement HealthCheckPort",
                provider=provider,
            )
            return HealthResult(
                provider=provider,
                status="unknown",
                error="Adapter does not implement HealthCheckPort",
                checked_at=self.clock.now(),
            )

        except _HEALTH_SERVICE_ERRORS as e:
            self.logger.error(
                "Health check failed",
                provider=provider,
                error=str(e),
            )
            return HealthResult(
                provider=provider,
                status="unhealthy",
                error=str(e),
                checked_at=self.clock.now(),
            )

    async def _run_adapter_health_check(
        self,
        adapter: HealthCheckPort,
    ) -> HealthCheckResult:
        """Run adapter health probe inside HTTP client context when available.

        Provider health probes call ``UnifiedHTTPClient.get_once`` and require an
        entered async client lifecycle. Adapters do not always own that entry
        point for one-shot diagnostics checks.
        """
        http_client = getattr(adapter, "http_client", None)
        if http_client is None:
            http_client = getattr(adapter, "_http_client", None)
        enter = getattr(http_client, "__aenter__", None)
        exit_ = getattr(http_client, "__aexit__", None)
        if http_client is not None and callable(enter) and callable(exit_):
            # Narrowed non-None client; cast for static OptionalContextManager.
            client = cast(Any, http_client)  # Any: duck-typed async HTTP client context
            async with client:
                return await adapter.check_health()
        return await adapter.check_health()

    def list_available_providers(self) -> list[str]:
        """List all available providers that can be health checked.

        Returns:
            List of provider names.
        """
        providers: list[str] = self._factory.list_providers()
        self.logger.debug("Listed available providers", count=len(providers))
        return providers
