"""HTTP infrastructure components.

Provides:
- TokenBucketRateLimiter: Rate limiting (implements RateLimiterPort)
- CircuitBreakerGuard: Fault tolerance (implements CircuitBreakerPort)
- UnifiedHTTPClient: Async HTTP client with rate limiting and circuit breaker
- RetryConfig: Configuration for retry strategies
- ProviderHealthMonitor: Centralized provider health monitoring (RULES.md §3.5)
- ProviderHealthTracker: Per-provider health state machine wrapper
- HealthAdjustedConfig: Health-based client configuration adjustments
"""

from __future__ import annotations

from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.client import RetryConfig, UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.health_monitor import (
    HealthAdjustedConfig,
    ProviderHealthMonitor,
    ProviderHealthState,
    ProviderHealthTracker,
)
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter

__all__ = [
    "CircuitBreakerGuard",
    "HealthAdjustedConfig",
    "ProviderHealthMonitor",
    "ProviderHealthState",
    "ProviderHealthTracker",
    "RetryConfig",
    "TokenBucketRateLimiter",
    "UnifiedHTTPClient",
]
