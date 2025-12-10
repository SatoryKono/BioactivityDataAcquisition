"""
Tests for factory implementations.
"""

import os
from unittest.mock import Mock, patch

from bioetl.domain.observability import LoggingPortABC
from bioetl.infrastructure.clients.base.factories import (
    EnvSecretProviderImpl,
    default_cache,
    default_rate_limiter,
    default_secret_provider,
)
from bioetl.infrastructure.clients.base.impl.cache import MemoryCacheImpl
from bioetl.infrastructure.clients.base.impl.rate_limiter import (
    TokenBucketRateLimiterImpl,
)


def test_default_factories():
    """Test default factories return correct implementations."""
    mock_logger = Mock(spec=LoggingPortABC)
    assert isinstance(default_rate_limiter(mock_logger), TokenBucketRateLimiterImpl)
    assert isinstance(default_cache(), MemoryCacheImpl)


def test_env_secret_provider():
    """Test environment secret provider."""
    provider = default_secret_provider()
    assert isinstance(provider, EnvSecretProviderImpl)

    with patch.dict(os.environ, {"TEST_SECRET": "s3cret"}):
        assert provider.get_secret("TEST_SECRET") == "s3cret"
        assert provider.get_secret("UNKNOWN") is None
