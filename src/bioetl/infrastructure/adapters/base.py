"""Base HTTP adapter for BioETL infrastructure.

Provides common functionality for adapters interacting with HTTP APIs,
including lifecycle management (context manager) and health checks.

Uses Template Method pattern for health checks: subclasses implement
_probe_health() for provider-specific probes, with automatic fallback
to circuit breaker assessment on failure.

Error Handling (RULES.md §4.1):
- Critical errors: Fail immediately (401, 403)
- Recoverable errors: Handled by UnifiedHTTPClient retry
- Data quality errors: Log and skip record

Health Check Observability (RULES.md §4.8):
- HEALTHY: DEBUG log "health_check_passed", increment healthy counter
- DEGRADED: WARNING log "health_check_degraded", increment degraded counter
- FAILED/UNHEALTHY: WARNING log "health_check_failed"/"health_check_unhealthy", increment failure counter
- LATENCY: Record duration histogram for all health checks
"""

from __future__ import annotations

__all__ = [
    "BaseHttpAdapter",
    "build_json_accept_headers",
    "build_mailto_user_agent_headers",
]

from types import TracebackType
from typing import TYPE_CHECKING, Self

from bioetl.domain.ports import (
    DataSourcePort,
    ErrorHandlerPort,
    LoggerPort,
    MetricsPort,
)
from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
from bioetl.infrastructure.adapters.common.adapter_defaults import (
    create_default_adapter_metrics,
    create_default_error_handler,
    create_default_request_collector,
)
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.health_check_mixin import HealthCheckProviderMixin

if TYPE_CHECKING:
    from collections.abc import Mapping

    from bioetl.domain.ports import CircuitBreakerPort
    from bioetl.infrastructure.adapters.common import HttpAdapterDependencyContext
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


def build_json_accept_headers(
    user_agent: str,
    *,
    correlation_id: object | None = None,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build the canonical JSON request-header set for BioETL adapters."""
    headers: dict[str, str] = {
        "User-Agent": user_agent,
        "Accept": "application/json",
    }
    if correlation_id is not None:
        headers["X-Correlation-ID"] = str(correlation_id)
    if extra_headers is not None:
        headers.update(extra_headers)
    return headers


def build_mailto_user_agent_headers(mailto: str) -> dict[str, str]:
    """Build the canonical polite-pool header set for mailto-aware providers."""
    return build_json_accept_headers(f"BioETL/1.0 (mailto:{mailto})")


class BaseHttpAdapter(HealthCheckProviderMixin, DataSourcePort):
    """Base class for HTTP adapters.

    Enforces usage of UnifiedHTTPClient and standardizes lifecycle management.

    Uses Template Method pattern for health checks via HealthCheckProviderMixin:
    - health_check(): Template method that handles try/except with observability
    - _probe_health(): Override for provider-specific health probe
    - _fallback_health_status(): Fallback using circuit breaker state

    Health Check Observability (via HealthCheckProviderMixin):
    - HEALTHY: DEBUG log, healthy counter, latency histogram
    - DEGRADED: WARNING log, degraded counter, latency histogram
    - FAILED/UNHEALTHY: WARNING log with details, failure counter, latency histogram

    Error Handling:
    - _error_handler: Provides unified error classification, logging, and wrapping

    Attributes:
        http_client: UnifiedHTTPClient instance for making HTTP requests.
        provider_name: Unique identifier for the data provider.
        logger: LoggerPort instance for structured logging.
        metrics: MetricsPort instance for metrics collection.

    """

    http_client: UnifiedHTTPClient
    provider_name: str
    logger: LoggerPort
    metrics: MetricsPort | None
    _metrics: MetricsPort | None
    _error_handler: ErrorHandlerPort
    _adapter_metrics: AdapterMetricsRecorder
    _request_collector: APIRequestCollector

    def __init__(
        self,
        http_client: UnifiedHTTPClient,
        logger: LoggerPort,
        metrics: MetricsPort | None = None,
        *,
        dependency_context: HttpAdapterDependencyContext | None = None,
        error_handler: ErrorHandlerPort | None = None,
        adapter_metrics: AdapterMetricsRecorder | None = None,
        request_collector: APIRequestCollector | None = None,
    ) -> None:
        """Initialize BaseAdapter.

        Args:
            http_client: HTTP client for requests.
            logger: LoggerPort instance for structured logging (required).
            metrics: MetricsPort instance for metrics collection (optional).
            dependency_context: Explicit composition-owned dependency bundle for
                    runtime adapter collaborators. When provided, it is the
                    authoritative source for metrics, error handling, request
                    collection, and adapter metrics.
            error_handler: Pre-built error handler (optional, injected by
                    AdapterHelpersFactory). Falls back to inline AdapterErrorHandler.
            adapter_metrics: Pre-built adapter metrics (optional, injected by
                    AdapterHelpersFactory). Falls back to inline AdapterMetricsRecorder.
            request_collector: Pre-built request collector (optional, injected by
                    AdapterHelpersFactory). Falls back to inline APIRequestCollector.

        """
        self._http_client = http_client
        self.http_client = http_client  # Public alias for IDMappingHealthMixin and other protocol mixins
        self._logger = logger
        self.logger = logger  # Public alias required by HealthCheckMixin
        if dependency_context is not None:
            self._metrics = dependency_context.metrics
            self.metrics = dependency_context.metrics
            self._error_handler = dependency_context.error_handler
            self._adapter_metrics = dependency_context.adapter_metrics
            self._request_collector = dependency_context.request_collector
            return

        self._metrics = metrics
        self.metrics = self._metrics
        self._error_handler = (
            error_handler
            if error_handler is not None
            else create_default_error_handler(logger=logger, metrics=self._metrics)
        )
        if adapter_metrics is not None and request_collector is not None:
            self._adapter_metrics = adapter_metrics
            self._request_collector = request_collector
            return
        self._init_adapter_metrics()

    def __getattr__(self, name: str) -> object:
        """Resolve private runtime aliases for dataclass-based adapters.

        Some adapters are dataclasses and initialize public attributes
        (``http_client``, ``logger``, ``metrics``) without calling this base
        ``__init__``. This fallback keeps runtime behavior consistent by lazily
        binding the corresponding private aliases used across adapter code.
        """
        if name == "_http_client":
            http_client = self.__dict__.get("http_client")
            if http_client is not None:
                object.__setattr__(self, "_http_client", http_client)
                return http_client
        elif name == "_logger":
            logger = self.__dict__.get("logger")
            if logger is not None:
                object.__setattr__(self, "_logger", logger)
                return logger
        elif name == "_metrics":
            metrics = self.__dict__.get("metrics")
            object.__setattr__(self, "_metrics", metrics)
            return metrics

        raise AttributeError(f"{type(self).__name__} object has no attribute {name!r}")

    def _init_adapter_metrics(self) -> None:
        """Initialize adapter metrics and request collector.

        Creates standardized AdapterMetricsRecorder and APIRequestCollector instances.

        Called automatically from ``__init__``. For ``@dataclass`` subclasses
        that bypass ``__init__``, call explicitly from ``__post_init__``.

        """
        self._adapter_metrics = create_default_adapter_metrics(
            metrics=self._metrics,
            provider=self.provider_name,
        )
        self._request_collector = create_default_request_collector()

    def _bootstrap_dataclass_http_adapter(self) -> None:
        """Initialize base runtime for dataclass-style HTTP adapters.

        Dataclass adapters expose the standard public constructor fields but do
        not automatically execute ``BaseHttpAdapter.__init__``. Centralizing the
        bootstrap here removes repeated argument plumbing from provider clients.
        """
        BaseHttpAdapter.__init__(
            self,
            http_client=self.http_client,
            logger=self.logger,
            metrics=getattr(self, "metrics", None),
            dependency_context=getattr(self, "dependency_context", None),
            error_handler=getattr(self, "error_handler", None),
            adapter_metrics=getattr(self, "adapter_metrics", None),
            request_collector=getattr(self, "request_collector", None),
        )

    def _bind_fallback_fetch_service(self, fallback_fetch_service: object) -> None:
        """Bind the canonical fallback orchestrator on adapters that use one."""
        self._fallback_fetch_service = fallback_fetch_service

    @property
    def _circuit_breaker(self) -> CircuitBreakerPort:
        """Return circuit breaker from HTTP client.

        Implements abstract property from HealthCheckProviderMixin.

        Returns:
            CircuitBreakerPort instance for health status assessment.

        """
        return self._http_client.circuit_breaker

    async def __aenter__(self) -> Self:
        """Enter async context manager.

        Delegates to the underlying HTTP client.
        """
        await self._http_client.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager.

        Delegates to the underlying HTTP client.
        """
        await self._http_client.__aexit__(exc_type, exc_val, exc_tb)

    async def aclose(self) -> None:
        """Close resources.

        Base implementation is a no-op as HTTP client is managed by context.
        Subclasses can override if they manage additional resources.
        """

    async def _close_http_client_context(self) -> None:
        """Close the wrapped HTTP client context when the adapter owns one."""
        await self._http_client.__aexit__(None, None, None)
