"""Factories for infrastructure client helpers (cache, retry, rate limit).

All factories require explicit dependencies - no implicit defaults.
Use CompositionRoot for creating instances with default implementations.

Naming convention:
- create_*() - creates a new instance each time
- get_*() - returns singleton/cached instance
- build_*() - uses builder pattern with HttpClientConfig
"""

import os
from typing import Any
import warnings

import requests

from bioetl.domain.clients.base.contracts import (
    CacheABC,
    PaginatorABC,
    RateLimiterABC,
    RequestBuilderABC,
    SecretProviderABC,
)
from bioetl.domain.configs import HttpClientConfig
from bioetl.domain.observability import LoggingPortABC, MetricsPortABC
from bioetl.domain.ports.parsing import ResponseParserPortABC
from bioetl.infrastructure.clients.base.http_error_handler import (
    DefaultHttpErrorHandler,
    HttpErrorHandlerABC,
)
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
    ChemblGenericResponseParser,
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


def create_rate_limiter(
    logger: LoggingPortABC,
    rate: float = _DEFAULT_HTTP_CONFIG.rate_limit_per_sec,
    capacity: float | None = None,
) -> RateLimiterABC:
    """Create a rate limiter with token bucket semantics.

    Args:
        logger: Required logger instance
        rate: Tokens per second
        capacity: Maximum bucket capacity

    Returns:
        Configured rate limiter
    """
    resolved_capacity = capacity if capacity is not None else max(1.0, rate)
    return TokenBucketRateLimiterImpl(rate, resolved_capacity, logger)


def create_cache() -> CacheABC[Any]:
    """Create a new in-memory cache instance."""

    return MemoryCacheImpl()


def create_secret_provider() -> SecretProviderABC:
    """Create an environment-backed secret provider instance."""

    return EnvSecretProviderImpl()


def create_request_builder(*, base_url: str | None = None) -> RequestBuilderABC:
    """Create a new request builder instance.

    Requires explicit base_url; raises if not provided to avoid silent misuse.
    """

    if not base_url:
        raise NotImplementedError("create_request_builder requires base_url")
    return ChemblRequestBuilderImpl(base_url)


def create_response_parser() -> ResponseParserPortABC:
    """Create a new response parser instance."""

    return ChemblGenericResponseParser()


def create_paginator() -> PaginatorABC:
    """Create a new paginator instance."""

    return ChemblPaginatorImpl()


def create_api_client(
    provider: str,
    config: HttpClientConfig,
    logger: LoggingPortABC,
    metrics: MetricsPortABC,
    *,
    base_client: Any | None = None,
) -> _HttpTransport:
    """Create a new API client without middleware indirection.

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
    error_handler: HttpErrorHandlerABC | None = None,
) -> _HttpTransport:
    """Construct HTTP client using HttpClientConfig.

    Args:
        provider: Provider identifier
        logger: Required logger instance
        metrics: Required metrics instance
        config: Optional HTTP config
        base_client: Optional pre-configured HTTP client
        error_handler: Optional HTTP error handler (defaults to DefaultHttpErrorHandler)

    Returns:
        Configured HTTP transport
    """
    resolved_config = _ensure_http_config(config)
    resolved_client = base_client if base_client is not None else requests.Session()
    resolved_error_handler = error_handler or DefaultHttpErrorHandler(logger)
    return _HttpTransport(
        provider=provider,
        config=resolved_config,
        base_client=resolved_client,
        logger=logger,
        metrics=metrics,
        error_handler=resolved_error_handler,
    )


# ---------------------------------------------------------------------------
# Deprecated aliases for backward compatibility
# ---------------------------------------------------------------------------


def default_rate_limiter(
    logger: LoggingPortABC,
    rate: float = _DEFAULT_HTTP_CONFIG.rate_limit_per_sec,
    capacity: float | None = None,
) -> RateLimiterABC:
    """DEPRECATED: Use create_rate_limiter() instead."""
    warnings.warn(
        "default_rate_limiter is deprecated, use create_rate_limiter instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return create_rate_limiter(logger, rate, capacity)


def default_cache() -> CacheABC[Any]:
    """DEPRECATED: Use create_cache() instead."""
    warnings.warn(
        "default_cache is deprecated, use create_cache instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return create_cache()


def default_secret_provider() -> SecretProviderABC:
    """DEPRECATED: Use create_secret_provider() instead."""
    warnings.warn(
        "default_secret_provider is deprecated, use create_secret_provider instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return create_secret_provider()


def default_request_builder(*, base_url: str | None = None) -> RequestBuilderABC:
    """DEPRECATED: Use create_request_builder() instead."""
    warnings.warn(
        "default_request_builder is deprecated, use create_request_builder instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return create_request_builder(base_url=base_url)


def default_response_parser() -> ResponseParserPortABC:
    """DEPRECATED: Use create_response_parser() instead."""
    warnings.warn(
        "default_response_parser is deprecated, use create_response_parser instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return create_response_parser()


def default_paginator() -> PaginatorABC:
    """DEPRECATED: Use create_paginator() instead."""
    warnings.warn(
        "default_paginator is deprecated, use create_paginator instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return create_paginator()


def default_api_client(
    provider: str,
    config: HttpClientConfig,
    logger: LoggingPortABC,
    metrics: MetricsPortABC,
    *,
    base_client: Any | None = None,
) -> _HttpTransport:
    """DEPRECATED: Use create_api_client() instead."""
    warnings.warn(
        "default_api_client is deprecated, use create_api_client instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return create_api_client(provider, config, logger, metrics, base_client=base_client)
