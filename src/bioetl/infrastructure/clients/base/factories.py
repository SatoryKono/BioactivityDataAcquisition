"""Factories for infrastructure client helpers (cache, retry, rate limit).

All factories require explicit dependencies - no implicit defaults.
Use CompositionRoot for creating instances with default implementations.
"""

import os
from typing import Any

import requests

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
    logger: LoggingPortABC,
    *,
    config: HttpClientConfig | None = None,
) -> RateLimiterABC:
    """Create a rate limiter using HTTP config.

    Args:
        logger: Required logger instance
        config: Optional HTTP config for rate settings

    Returns:
        Configured rate limiter
    """
    resolved = _ensure_http_config(config)
    rate = resolved.rate_limit_per_sec
    capacity = max(1.0, rate)
    return TokenBucketRateLimiterImpl(rate, capacity, logger)


def default_rate_limiter(
    logger: LoggingPortABC,
    rate: float = _DEFAULT_HTTP_CONFIG.rate_limit_per_sec,
    capacity: float | None = None,
) -> RateLimiterABC:
    """Create the default rate limiter with token bucket semantics.

    Args:
        logger: Required logger instance
        rate: Tokens per second
        capacity: Maximum bucket capacity

    Returns:
        Configured rate limiter
    """
    resolved_capacity = capacity if capacity is not None else max(1.0, rate)
    return TokenBucketRateLimiterImpl(rate, resolved_capacity, logger)


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
    logger: LoggingPortABC,
    metrics: MetricsPortABC,
    *,
    base_client: Any | None = None,
) -> _HttpTransport:
    """Create the default API client without middleware indirection.

    Args:
        provider: Provider identifier
        config: HTTP client configuration
        logger: Required logger instance
        metrics: Required metrics instance
        base_client: Optional pre-configured HTTP client

    Returns:
        Configured HTTP transport
    """
    return build_http_client(
        provider,
        logger=logger,
        metrics=metrics,
        config=config,
        base_client=base_client,
    )


def build_http_client(
    provider: str,
    logger: LoggingPortABC,
    metrics: MetricsPortABC,
    *,
    config: HttpClientConfig | None = None,
    base_client: Any | None = None,
) -> _HttpTransport:
    """Construct HTTP client using HttpClientConfig.

    Args:
        provider: Provider identifier
        logger: Required logger instance
        metrics: Required metrics instance
        config: Optional HTTP config
        base_client: Optional pre-configured HTTP client

    Returns:
        Configured HTTP transport
    """
    resolved_config = _ensure_http_config(config)
    resolved_client = base_client if base_client is not None else requests.Session()
    return _HttpTransport(
        provider=provider,
        config=resolved_config,
        base_client=resolved_client,
        logger=logger,
        metrics=metrics,
    )
