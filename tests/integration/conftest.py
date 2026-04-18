"""Fixtures for integration tests."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter


def _build_token_bucket_rate_limiter() -> TokenBucketRateLimiter:
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter

    return TokenBucketRateLimiter(rate=10.0, capacity=100)


def _build_circuit_breaker_guard() -> CircuitBreakerGuard:
    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard

    return CircuitBreakerGuard(provider="integration_test")


@pytest.fixture(scope="session", autouse=True)
def integration_relaxed_dq() -> None:
    """Relax DQ thresholds for integration tests using VCR cassettes."""
    os.environ["BIOETL_TEST_RELAXED_DQ"] = "1"
    os.environ["BIOETL_PIPELINE__RELAXED_DQ"] = "1"


@pytest.fixture
def token_bucket() -> TokenBucketRateLimiter:
    """Default rate limiter for integration HTTP clients."""
    return _build_token_bucket_rate_limiter()


@pytest.fixture
def circuit_breaker() -> CircuitBreakerGuard:
    """Default circuit breaker for integration HTTP clients."""
    return _build_circuit_breaker_guard()
