"""HTTP infrastructure components.

Provides:
- TokenBucket: Rate limiting (implements RateLimiterPort)
- CircuitBreaker: Fault tolerance (implements CircuitBreakerPort)
- UnifiedHTTPClient: Async HTTP client with rate limiting and circuit breaker
- RetryConfig: Backward compatibility alias for RetryPolicy
- ProviderHealthMonitor: Centralized provider health monitoring (RULES.md §3.5)
"""

from __future__ import annotations

from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import RetryConfig, UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.health_monitor import (
    ProviderHealthMonitor,
    ProviderHealthState,
)
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket

__all__ = [
    "CircuitBreaker",
    "ProviderHealthMonitor",
    "ProviderHealthState",
    "RetryConfig",
    "TokenBucket",
    "UnifiedHTTPClient",
]
