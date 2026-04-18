"""Unified HTTP client facade with retry/limiter/circuit-breaker orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import httpx

from bioetl.domain.resilience import RetryConfig
from bioetl.infrastructure.adapters.http.client_context_mixin import (
    HTTPClientContextMixin,
)
from bioetl.infrastructure.adapters.http.client_request_methods_mixin import (
    HTTPClientRequestMethodsMixin,
)
from bioetl.infrastructure.adapters.http.client_retry_mixin import HTTPClientRetryMixin

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        CircuitBreakerPort,
        LoggerPort,
        MetricsPort,
        RateLimiterPort,
        TracingPort,
    )
    from bioetl.domain.types import RunID


__all__ = ["RetryConfig", "UnifiedHTTPClient"]


@dataclass
class UnifiedHTTPClient(
    HTTPClientContextMixin, HTTPClientRetryMixin, HTTPClientRequestMethodsMixin
):
    """Async HTTP client facade with resilience and observability ports."""

    rate_limiter: RateLimiterPort
    circuit_breaker: CircuitBreakerPort
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    timeout: float = 30.0
    read_timeout_multiplier: float = 2.0
    run_id: RunID | None = None
    user_agent: str = "BioETL/5.0.0"
    contact_email: str | None = None
    provider: str = "unknown"
    max_connections: int = 50
    max_keepalive_connections: int = 10
    trust_env: bool = True
    tracer: TracingPort | None = None
    metrics: MetricsPort | None = None
    logger: LoggerPort | None = None

    _client: httpx.AsyncClient | None = field(init=False, default=None)
    _tracer: TracingPort | None = field(init=False)
    _metrics: MetricsPort | None = field(init=False)

    def __post_init__(self) -> None:
        """Capture injected observability ports without local fallback creation."""
        self._tracer = self.tracer
        self._metrics = self.metrics
