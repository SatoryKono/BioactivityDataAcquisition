# MRO/override residual on mixin or client hierarchies.
"""Base HTTP adapter for BioETL infrastructure.

Provides common functionality for adapters interacting with HTTP APIs,
including lifecycle management (context manager) and health checks.

Uses Template Method pattern for health checks: subclasses implement
_probe_health() for provider-specific probes, with automatic fallback
to circuit breaker assessment on failure.
"""

from __future__ import annotations

__all__ = [
    "BaseHttpAdapter",
    "build_json_accept_headers",
    "build_mailto_user_agent_headers",
]

from typing import TYPE_CHECKING, Self, override

from bioetl.domain.ports import (
    DataSourcePort,
    ErrorHandlerPort,
    LoggerPort,
    MetricsPort,
)
from bioetl.infrastructure.adapters._base_headers import (
    build_json_accept_headers,
    build_mailto_user_agent_headers,
)
from bioetl.infrastructure.adapters._base_http_client import (
    _HttpClientWithCircuitBreaker,
)
from bioetl.infrastructure.adapters._base_runtime import (
    apply_dependency_context,
    init_default_adapter_metrics,
    init_inline_adapter_collaborators,
    resolve_lazy_private_alias,
)
from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.health_check_mixin import HealthCheckProviderMixin

if TYPE_CHECKING:
    from types import TracebackType

    from bioetl.domain.ports import CircuitBreakerPort
    from bioetl.infrastructure.adapters.common import HttpAdapterDependencyContext


class BaseHttpAdapter(HealthCheckProviderMixin, DataSourcePort):  # pyright: ignore[reportImplicitAbstractClass]
    """Base class for HTTP adapters with UnifiedHTTPClient lifecycle + health checks."""

    http_client: _HttpClientWithCircuitBreaker
    provider_name: str  # pyright: ignore[reportIncompatibleMethodOverride]
    logger: LoggerPort
    metrics: MetricsPort | None
    _metrics: MetricsPort | None
    _error_handler: ErrorHandlerPort
    _adapter_metrics: AdapterMetricsRecorder
    _request_collector: APIRequestCollector

    def __init__(
        self,
        http_client: _HttpClientWithCircuitBreaker,
        logger: LoggerPort,
        metrics: MetricsPort | None = None,
        *,
        dependency_context: HttpAdapterDependencyContext | None = None,
        error_handler: ErrorHandlerPort | None = None,
        adapter_metrics: AdapterMetricsRecorder | None = None,
        request_collector: APIRequestCollector | None = None,
    ) -> None:
        """Initialize BaseAdapter collaborators from context or inline defaults."""
        self._http_client = http_client
        self.http_client = http_client  # Public alias for IDMappingHealthMixin and other protocol mixins
        self._logger = logger
        self.logger = logger  # Public alias required by HealthCheckMixin
        if dependency_context is not None:
            apply_dependency_context(self, dependency_context)
            return

        if init_inline_adapter_collaborators(
            self,
            logger=logger,
            metrics=metrics,
            error_handler=error_handler,
            adapter_metrics=adapter_metrics,
            request_collector=request_collector,
        ):
            return
        self._init_adapter_metrics()

    def __getattr__(self, name: str) -> object:
        """Resolve private runtime aliases for dataclass-based adapters."""
        handled, value = resolve_lazy_private_alias(self, name)
        if handled:
            return value
        raise AttributeError(f"{type(self).__name__} object has no attribute {name!r}")

    def _init_adapter_metrics(self) -> None:
        """Initialize adapter metrics and request collector."""
        init_default_adapter_metrics(
            self,
            metrics=self._metrics,
            provider_name=self.provider_name,
        )

    def _bootstrap_dataclass_http_adapter(self) -> None:
        """Initialize base runtime for dataclass-style HTTP adapters."""
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
    @override
    def _circuit_breaker(self) -> CircuitBreakerPort:
        """Return circuit breaker from HTTP client."""
        return self._http_client.circuit_breaker

    async def __aenter__(self) -> Self:
        """Enter async context manager via the underlying HTTP client."""
        await self._http_client.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager via the underlying HTTP client."""
        await self._http_client.__aexit__(exc_type, exc_val, exc_tb)

    async def aclose(self) -> None:
        """Close resources (no-op base; HTTP client is context-managed)."""

    async def _close_http_client_context(self) -> None:
        """Close the wrapped HTTP client context when the adapter owns one."""
        await self._http_client.__aexit__(None, None, None)
