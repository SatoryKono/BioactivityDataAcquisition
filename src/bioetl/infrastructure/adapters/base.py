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
- SUCCESS: DEBUG log "health_check_passed", increment success counter
- FAILURE: WARNING log "health_check_failed" with details, increment failure counter
- LATENCY: Record duration histogram for all health checks
"""

from __future__ import annotations

__all__ = ["BaseHttpAdapter"]

from types import TracebackType
from typing import TYPE_CHECKING, Self

from bioetl.domain.ports import (
    DataSourcePort,
    ErrorHandlerPort,
    LoggerPort,
    MetricsPort,
    NoOpMetrics,
)
from bioetl.infrastructure.adapters.base_metrics import AdapterMetrics
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.error_handling import ErrorService
from bioetl.infrastructure.adapters.health_check_mixin import HealthCheckProviderMixin

if TYPE_CHECKING:
    from bioetl.domain.ports import CircuitBreakerPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


class BaseHttpAdapter(HealthCheckProviderMixin, DataSourcePort):
    """Base class for HTTP adapters.

    Enforces usage of UnifiedHTTPClient and standardizes lifecycle management.

    Uses Template Method pattern for health checks via HealthCheckProviderMixin:
    - health_check(): Template method that handles try/except with observability
    - _probe_health(): Override for provider-specific health probe
    - _fallback_health_status(): Fallback using circuit breaker state

    Health Check Observability (via HealthCheckProviderMixin):
    - SUCCESS: DEBUG log, success counter, latency histogram
    - FAILURE: WARNING log with details, failure counter, latency histogram

    Error Handling:
    - _error_handler: Provides unified error classification, logging, and wrapping

    Attributes:
        http_client: UnifiedHTTPClient instance for making HTTP requests.
        provider_name: Unique identifier for the data provider.
        logger: LoggerPort instance for structured logging.
        metrics: MetricsPort instance for metrics collection (defaults to NoOpMetrics).

    """

    http_client: UnifiedHTTPClient
    provider_name: str
    logger: LoggerPort
    metrics: MetricsPort | None  # Runtime-resolved to NoOpMetrics if None
    _error_handler: ErrorHandlerPort
    _adapter_metrics: AdapterMetrics
    _request_collector: APIRequestCollector

    def __init__(
        self,
        http_client: UnifiedHTTPClient,
        logger: LoggerPort,
        metrics: MetricsPort | None = None,
        *,
        error_handler: ErrorHandlerPort | None = None,
        adapter_metrics: AdapterMetrics | None = None,
        request_collector: APIRequestCollector | None = None,
    ) -> None:
        """Initialize BaseAdapter.

        Args:
            http_client: HTTP client for requests.
            logger: LoggerPort instance for structured logging (required).
            metrics: MetricsPort instance for metrics collection (optional).
                    Defaults to NoOpMetrics if not provided.
            error_handler: Pre-built error handler (optional, injected by
                    AdapterHelpersFactory). Falls back to inline ErrorService.
            adapter_metrics: Pre-built adapter metrics (optional, injected by
                    AdapterHelpersFactory). Falls back to inline AdapterMetrics.
            request_collector: Pre-built request collector (optional, injected by
                    AdapterHelpersFactory). Falls back to inline APIRequestCollector.

        """
        self._http_client = http_client
        self._logger = logger
        self._metrics = metrics if metrics is not None else NoOpMetrics()
        self._error_handler = (
            error_handler
            if error_handler is not None
            else ErrorService(logger, metrics=self._metrics)
        )
        if adapter_metrics is not None and request_collector is not None:
            self._adapter_metrics = adapter_metrics
            self._request_collector = request_collector
        else:
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
            metrics_port = metrics if metrics is not None else NoOpMetrics()
            object.__setattr__(self, "_metrics", metrics_port)
            return metrics_port

        raise AttributeError(f"{type(self).__name__} object has no attribute {name!r}")

    def _init_adapter_metrics(self) -> None:
        """Initialize adapter metrics and request collector.

        Creates standardized AdapterMetrics and APIRequestCollector instances.
        Resolves None metrics to NoOpMetrics for the metrics port.

        Called automatically from ``__init__``. For ``@dataclass`` subclasses
        that bypass ``__init__``, call explicitly from ``__post_init__``.

        """
        metrics_port = self._metrics if self._metrics is not None else NoOpMetrics()
        self._adapter_metrics = AdapterMetrics(metrics_port, self.provider_name)
        self._request_collector = APIRequestCollector()

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
