"""HTTP infrastructure components.

Provides:
- TokenBucket: Rate limiting (implements RateLimiterPort)
- CircuitBreaker: Fault tolerance (implements CircuitBreakerPort)
- UnifiedHTTPClient: Async HTTP client with rate limiting and circuit breaker
- RetryConfig: Backward compatibility alias for RetryPolicy
- ProviderHealthMonitor: Centralized provider health monitoring (RULES.md §3.5)
- ProviderHealthTracker: Per-provider health state machine wrapper
- HealthAdjustedConfig: Health-based client configuration adjustments
"""

from __future__ import annotations

from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import RetryConfig, UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.health_monitor import (
    HealthAdjustedConfig,
    ProviderHealthMonitor,
    ProviderHealthState,
    ProviderHealthTracker,
)
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket

# Backward compatibility alias
AdjustedClientConfig = HealthAdjustedConfig

__all__ = [
    "AdjustedClientConfig",  # Backward compatibility alias
    "CircuitBreaker",
    "HealthAdjustedConfig",
    "ProviderHealthMonitor",
    "ProviderHealthState",
    "ProviderHealthTracker",
    "RetryConfig",
    "TokenBucket",
    "UnifiedHTTPClient",
]
