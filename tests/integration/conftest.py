"""Fixtures for integration tests."""

from __future__ import annotations

import os

import pytest

from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter


@pytest.fixture(scope="session", autouse=True)
def integration_relaxed_dq() -> None:
    """Relax DQ thresholds for integration tests using VCR cassettes."""
    os.environ["BIOETL_TEST_RELAXED_DQ"] = "1"


@pytest.fixture
def token_bucket() -> TokenBucketRateLimiter:
    """Default rate limiter for integration HTTP clients."""
    return TokenBucketRateLimiter(rate=10.0, capacity=100)


@pytest.fixture
def circuit_breaker() -> CircuitBreakerGuard:
    """Default circuit breaker for integration HTTP clients."""
    return CircuitBreakerGuard(provider="integration_test")
