"""
Tests for factory implementations.
"""
import os
from unittest.mock import patch

from bioetl.infrastructure.clients.base.factories import (
    EnvSecretProvider,
    default_cache,
    default_rate_limiter,
    default_retry_policy,
    default_secret_provider,
)
from bioetl.infrastructure.clients.base.impl.cache import MemoryCacheImpl
from bioetl.infrastructure.clients.base.impl.rate_limiter import (
    TokenBucketRateLimiterImpl,
)
from bioetl.infrastructure.clients.base.impl.retry_policy import (
    ExponentialBackoffRetryImpl,
)


def test_default_factories():
    """Test default factories return correct implementations."""
    assert isinstance(default_rate_limiter(), TokenBucketRateLimiterImpl)
    assert isinstance(default_retry_policy(), ExponentialBackoffRetryImpl)
    assert isinstance(default_cache(), MemoryCacheImpl)


def test_env_secret_provider():
    """Test environment secret provider."""
    provider = default_secret_provider()
    assert isinstance(provider, EnvSecretProvider)

    with patch.dict(os.environ, {"TEST_SECRET": "s3cret"}):
        assert provider.get_secret("TEST_SECRET") == "s3cret"
        assert provider.get_secret("UNKNOWN") is None
