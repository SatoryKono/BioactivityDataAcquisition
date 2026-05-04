"""Fixtures for integration tests."""

from __future__ import annotations

from collections.abc import Generator
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


def _clear_runtime_config_caches() -> None:
    """Clear runtime settings/config caches after environment mutations."""
    from bioetl.infrastructure.config import get_pipeline_config, get_settings
    from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config
    from bioetl.infrastructure.config.source_config_loader import load_source_config

    get_settings.cache_clear()
    get_pipeline_config.cache_clear()
    load_pipeline_config.cache_clear()
    load_source_config.cache_clear()


@pytest.fixture
def relaxed_dq_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Enable relaxed DQ thresholds explicitly for replay-heavy integration tests."""
    _clear_runtime_config_caches()
    monkeypatch.setenv("BIOETL_TEST_RELAXED_DQ", "1")
    monkeypatch.setenv("BIOETL_PIPELINE__RELAXED_DQ", "1")
    _clear_runtime_config_caches()
    yield
    _clear_runtime_config_caches()


@pytest.fixture
def strict_dq_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Force strict DQ mode for integration tests that validate strict behavior."""
    _clear_runtime_config_caches()
    monkeypatch.delenv("BIOETL_TEST_RELAXED_DQ", raising=False)
    monkeypatch.setenv("BIOETL_PIPELINE__RELAXED_DQ", "0")
    _clear_runtime_config_caches()
    yield
    _clear_runtime_config_caches()


@pytest.fixture
def token_bucket() -> TokenBucketRateLimiter:
    """Default rate limiter for integration HTTP clients."""
    return _build_token_bucket_rate_limiter()


@pytest.fixture
def circuit_breaker() -> CircuitBreakerGuard:
    """Default circuit breaker for integration HTTP clients."""
    return _build_circuit_breaker_guard()
