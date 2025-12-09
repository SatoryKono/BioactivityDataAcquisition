"""Factories for infrastructure client helpers (cache, retry, rate limit)."""

import os
from typing import Any

from bioetl.domain.clients.base.contracts import (
    ApiClientABC,
    CacheABC,
    PaginatorABC,
    RateLimiterABC,
    RequestBuilderABC,
    ResponseParserABC,
    SecretProviderABC,
    SideInputProviderABC,
)
from bioetl.domain.observability import LoggingPortABC
from bioetl.domain.configs import ClientConfig, HTTP_CLIENT_DEFAULTS, HttpClientDefaults
from bioetl.infrastructure.clients.base.impl.cache import MemoryCacheImpl
from bioetl.infrastructure.clients.base.impl.rate_limiter import (
    TokenBucketRateLimiterImpl,
)
from bioetl.infrastructure.clients.base.impl.unified_api_client_impl import (
    UnifiedAPIClientImpl,
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


def _resolve_http_defaults(
    *,
    client_config: ClientConfig | None = None,
    defaults: HttpClientDefaults | None = None,
) -> HttpClientDefaults:
    """Return explicit defaults or fall back to canonical HTTP defaults."""

    if client_config is None:
        return defaults or HTTP_CLIENT_DEFAULTS

    return HttpClientDefaults(
        timeout=int(client_config.timeout_sec),
        retries=client_config.max_retries,
        backoff_factor=client_config.backoff_factor,
        rate_limit=float(client_config.rate_limit_per_sec),
    )


def _ensure_client_config(
    *,
    client_config: ClientConfig | None = None,
    defaults: HttpClientDefaults | None = None,
) -> ClientConfig:
    """Return provided client config or build one from defaults."""

    if client_config is not None:
        return client_config

    resolved = defaults or HTTP_CLIENT_DEFAULTS
    return ClientConfig(
        timeout_sec=resolved.timeout,
        max_retries=resolved.retries,
        rate_limit_per_sec=resolved.rate_limit,
        backoff_factor=resolved.backoff_factor,
    )


def build_rate_limiter(
    *,
    client_config: ClientConfig | None = None,
    defaults: HttpClientDefaults | None = None,
    logger: LoggingPortABC | None = None,
) -> RateLimiterABC:
    """Create a rate limiter using unified HTTP defaults."""

    resolved_defaults = _resolve_http_defaults(
        client_config=client_config, defaults=defaults
    )
    rate = resolved_defaults.rate_limit
    capacity = max(1.0, rate)
    return TokenBucketRateLimiterImpl(rate, capacity, logger=logger)


def default_rate_limiter(
    rate: float = HTTP_CLIENT_DEFAULTS.rate_limit,
    capacity: float | None = None,
    *,
    logger: LoggingPortABC | None = None,
) -> RateLimiterABC:
    """Create the default rate limiter with token bucket semantics."""

    resolved_capacity = capacity if capacity is not None else max(1.0, rate)
    return TokenBucketRateLimiterImpl(
        rate, resolved_capacity, logger=logger
    )


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
    config: ClientConfig,
    *,
    base_client: Any | None = None,
    logger: LoggingPortABC | None = None,
) -> ApiClientABC:
    """Create the default API client without middleware indirection."""

    return build_http_client(
        provider,
        client_config=config,
        base_client=base_client,
        logger=logger,
    )


def build_http_client(
    provider: str,
    *,
    client_config: ClientConfig | None = None,
    defaults: HttpClientDefaults | None = None,
    base_client: Any | None = None,
    logger: LoggingPortABC | None = None,
) -> ApiClientABC:
    """Construct HTTP client using centralized defaults."""

    resolved_config = _ensure_client_config(
        client_config=client_config, defaults=defaults
    )
    return UnifiedAPIClientImpl(
        provider=provider,
        config=resolved_config,
        base_client=base_client,
        logger=logger,
    )


def default_side_input_provider() -> SideInputProviderABC:
    """Stub factory for side input providers until implemented."""

    raise NotImplementedError("SideInputProviderABC has no default implementation yet")
