"""HTTP infrastructure components.

Provides:
- TokenBucket: Rate limiting (implements RateLimiterPort)
- CircuitBreaker: Fault tolerance (implements CircuitBreakerPort)
- UnifiedHTTPClient: Async HTTP client with rate limiting and circuit breaker
- RetryConfig: Backward compatibility alias for RetryPolicy
- ProviderHealthMonitor: Centralized provider health monitoring (RULES.md §3.5)
- ProviderHealthTracker: Per-provider health state machine wrapper
- AdjustedClientConfig: Health-based client configuration adjustments
"""

from __future__ import annotations

from bioetl.domain.resilience import RetryConfig
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.health_monitor import (
    AdjustedClientConfig,
    ProviderHealthMonitor,
    ProviderHealthState,
    ProviderHealthTracker,
)
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket

__all__ = [
    "AdjustedClientConfig",
    "CircuitBreaker",
    "ProviderHealthMonitor",
    "ProviderHealthState",
    "ProviderHealthTracker",
    "RetryConfig",
    "TokenBucket",
    "UnifiedHTTPClient",
]
