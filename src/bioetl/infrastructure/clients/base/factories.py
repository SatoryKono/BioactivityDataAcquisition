"""Factories for infrastructure client helpers (cache, retry, rate limit)."""

import os
from typing import Any

from bioetl.domain.clients.base.contracts import (
    CacheABC,
    PaginatorABC,
    RateLimiterABC,
    RequestBuilderABC,
    ResponseParserABC,
    SecretProviderABC,
)
from bioetl.domain.configs import HttpClientConfig
from bioetl.domain.observability import LoggingPortABC, MetricsPortABC
from bioetl.infrastructure.clients.base.impl._http_transport import _HttpTransport
from bioetl.infrastructure.clients.base.impl.cache import MemoryCacheImpl
from bioetl.infrastructure.clients.base.impl.rate_limiter import (
    TokenBucketRateLimiterImpl,
)
from bioetl.infrastructure.clients.chembl.paginator import ChemblPaginatorImpl
from bioetl.infrastructure.clients.chembl.request_builder import (
    ChemblRequestBuilderImpl,
)
from bioetl.infrastructure.clients.chembl.response_parser import (
    ChemblResponseParserImpl,
)

# Default HTTP client configuration (single source of truth)
_DEFAULT_HTTP_CONFIG = HttpClientConfig()


class EnvSecretProviderImpl(SecretProviderABC):
    """Resolve secrets from environment variables."""

    def get_secret(self, name: str) -> str | None:
        """Fetch secret value from environment variables."""
        return os.getenv(name)


def _ensure_http_config(
    config: HttpClientConfig | dict[str, Any] | None = None,
) -> HttpClientConfig:
    """Normalize config to HttpClientConfig, falling back to defaults."""
    if config is None:
        return _DEFAULT_HTTP_CONFIG
    if isinstance(config, HttpClientConfig):
        return config
    return HttpClientConfig.model_validate(config)


def build_rate_limiter(
    *,
    config: HttpClientConfig | None = None,
    logger: LoggingPortABC | None = None,
) -> RateLimiterABC:
    """Create a rate limiter using HTTP config."""
    resolved = _ensure_http_config(config)
    rate = resolved.rate_limit_per_sec
    capacity = max(1.0, rate)
    return TokenBucketRateLimiterImpl(rate, capacity, logger=logger)


def default_rate_limiter(
    rate: float = _DEFAULT_HTTP_CONFIG.rate_limit_per_sec,
    capacity: float | None = None,
    *,
    logger: LoggingPortABC | None = None,
) -> RateLimiterABC:
    """Create the default rate limiter with token bucket semantics."""
    resolved_capacity = capacity if capacity is not None else max(1.0, rate)
    return TokenBucketRateLimiterImpl(rate, resolved_capacity, logger=logger)


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


def default_api_client(
    provider: str,
    config: HttpClientConfig,
    *,
    base_client: Any | None = None,
    logger: LoggingPortABC | None = None,
    metrics: MetricsPortABC | None = None,
) -> _HttpTransport:
    """Create the default API client without middleware indirection."""
    return build_http_client(
        provider,
        config=config,
        base_client=base_client,
        logger=logger,
        metrics=metrics,
    )


def build_http_client(
    provider: str,
    *,
    config: HttpClientConfig | None = None,
    base_client: Any | None = None,
    logger: LoggingPortABC | None = None,
    metrics: MetricsPortABC | None = None,
) -> _HttpTransport:
    """Construct HTTP client using HttpClientConfig."""
    resolved_config = _ensure_http_config(config)
    return _HttpTransport(
        provider=provider,
        config=resolved_config,
        base_client=base_client,
        logger=logger,
        metrics=metrics,
    )
