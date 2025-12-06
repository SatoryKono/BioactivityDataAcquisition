import os
from typing import Any

from bioetl.domain.clients.base.contracts import (
    CacheABC,
    RateLimiterABC,
    RetryPolicyABC,
    SecretProviderABC,
)
from bioetl.infrastructure.clients.base.impl.cache import MemoryCacheImpl
from bioetl.infrastructure.clients.base.impl.rate_limiter import (
    TokenBucketRateLimiterImpl,
)
from bioetl.infrastructure.clients.base.impl.retry_policy import (
    ExponentialBackoffRetryImpl,
)


class EnvSecretProvider(SecretProviderABC):
    def get_secret(self, name: str) -> str | None:
        return os.getenv(name)


def default_rate_limiter(rate: float = 10.0, capacity: float = 20.0) -> RateLimiterABC:
    return TokenBucketRateLimiterImpl(rate, capacity)


def default_retry_policy() -> RetryPolicyABC:
    return ExponentialBackoffRetryImpl()


def default_cache() -> CacheABC[Any]:
    return MemoryCacheImpl()


def default_secret_provider() -> SecretProviderABC:
    return EnvSecretProvider()
