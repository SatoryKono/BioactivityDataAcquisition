"""Factories for infrastructure client helpers (cache, retry, rate limit)."""

import os
from typing import Any

from bioetl.domain.clients.base.contracts import (
    CacheABC,
    PaginatorABC,
    RateLimiterABC,
    RequestBuilderABC,
    ResponseParserABC,
    RetryPolicyABC,
    SecretProviderABC,
    SideInputProviderABC,
)
from bioetl.infrastructure.clients.base.impl.cache import MemoryCacheImpl
from bioetl.infrastructure.clients.base.impl.rate_limiter import (
    TokenBucketRateLimiterImpl,
)
from bioetl.infrastructure.clients.base.impl.retry_policy import (
    ExponentialBackoffRetryImpl,
)
from bioetl.infrastructure.clients.chembl.paginator import ChemblPaginatorImpl
from bioetl.infrastructure.clients.chembl.request_builder import (
    ChemblRequestBuilderImpl,
)
from bioetl.infrastructure.clients.chembl.response_parser import (
    ChemblResponseParserImpl,
)


class EnvSecretProviderImpl(SecretProviderABC):
    """Resolve secrets from environment variables."""

    def get_secret(self, name: str) -> str | None:
        """Fetch secret value from environment variables."""
        return os.getenv(name)


def default_rate_limiter(rate: float = 10.0, capacity: float = 20.0) -> RateLimiterABC:
    """Create the default rate limiter with token bucket semantics."""

    return TokenBucketRateLimiterImpl(rate, capacity)


def default_retry_policy() -> RetryPolicyABC:
    """Provide a resilient retry policy with exponential backoff."""

    return ExponentialBackoffRetryImpl()


def default_cache() -> CacheABC[Any]:
    """Return the in-memory cache implementation."""

    return MemoryCacheImpl()


def default_secret_provider() -> SecretProviderABC:
    """Expose the environment-backed secret provider implementation."""

    return EnvSecretProviderImpl()


def default_request_builder(*, base_url: str | None = None) -> RequestBuilderABC:
    """
    Stub default request builder factory.

    Requires explicit base_url; raises if not provided to avoid silent misuse.
    """

    if not base_url:
        raise NotImplementedError("default_request_builder requires base_url")
    return ChemblRequestBuilderImpl(base_url)


def default_response_parser() -> ResponseParserABC:
    """Return the default response parser implementation."""

    return ChemblResponseParserImpl()


def default_paginator() -> PaginatorABC:
    """Return the default paginator implementation."""

    return ChemblPaginatorImpl()


def default_side_input_provider() -> SideInputProviderABC:
    """Stub factory for side input providers until implemented."""

    raise NotImplementedError("SideInputProviderABC has no default implementation yet")
