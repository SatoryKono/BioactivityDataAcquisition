"""
Composition Root for assembling the application's dependency graph.

This module is the single place where concrete implementations are instantiated
and wired together. No other module should create dependencies with default fallbacks.

Usage:
    # For production:
    root = CompositionRoot()
    http_transport = root.create_http_transport(provider="chembl", config=http_config)

    # For testing:
    root = CompositionRoot(
        logger=mock_logger,
        metrics=mock_metrics,
    )
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from bioetl.domain.clients.base.contracts import RateLimiterABC
from bioetl.domain.configs import HttpClientConfig
from bioetl.domain.observability import LoggingPortABC, MetricsPortABC
from bioetl.infrastructure.clients.base.impl._http_transport import _HttpTransport
from bioetl.infrastructure.clients.base.impl.rate_limiter import (
    TokenBucketRateLimiterImpl,
)
from bioetl.infrastructure.observability.factories import (
    default_logging_port,
    default_metrics_port,
)


@dataclass(frozen=True)
class ObservabilityStack:
    """Container for observability dependencies."""

    logger: LoggingPortABC
    metrics: MetricsPortABC


class CompositionRoot:
    """
    Central factory for creating application components with proper dependency injection.

    The composition root is the only place where default implementations are created.
    All other modules receive their dependencies explicitly.

    Example:
        >>> root = CompositionRoot()
        >>> transport = root.create_http_transport("chembl", HttpClientConfig())

        # For testing with mocks:
        >>> root = CompositionRoot(logger=mock_logger, metrics=mock_metrics)
        >>> transport = root.create_http_transport("chembl", HttpClientConfig())
    """

    def __init__(
        self,
        *,
        logger: LoggingPortABC | None = None,
        metrics: MetricsPortABC | None = None,
        http_session_factory: type | None = None,
    ) -> None:
        """
        Initialize composition root with optional overrides.

        Args:
            logger: Custom logger implementation (defaults to structured logger)
            metrics: Custom metrics implementation (defaults to Prometheus)
            http_session_factory: Factory for HTTP sessions (defaults to requests.Session)
        """
        self._logger = logger
        self._metrics = metrics
        self._http_session_factory = http_session_factory or requests.Session

    def get_logger(self) -> LoggingPortABC:
        """Get or create the logger instance."""
        if self._logger is None:
            self._logger = default_logging_port()
        return self._logger

    def get_metrics(self) -> MetricsPortABC:
        """Get or create the metrics instance."""
        if self._metrics is None:
            self._metrics = default_metrics_port()
        return self._metrics

    def get_observability_stack(self) -> ObservabilityStack:
        """Get the complete observability stack."""
        return ObservabilityStack(
            logger=self.get_logger(),
            metrics=self.get_metrics(),
        )

    def create_http_session(self) -> Any:
        """Create a new HTTP session."""
        return self._http_session_factory()

    def create_http_transport(
        self,
        provider: str,
        config: HttpClientConfig,
        *,
        base_client: Any | None = None,
    ) -> _HttpTransport:
        """
        Create an HTTP transport with all dependencies injected.

        Args:
            provider: Provider identifier (e.g., "chembl")
            config: HTTP client configuration
            base_client: Optional pre-configured HTTP client

        Returns:
            Fully configured _HttpTransport instance
        """
        return _HttpTransport(
            provider=provider,
            config=config,
            base_client=base_client or self.create_http_session(),
            logger=self.get_logger(),
            metrics=self.get_metrics(),
        )

    def create_rate_limiter(
        self,
        rate: float,
        capacity: float | None = None,
    ) -> RateLimiterABC:
        """
        Create a rate limiter with all dependencies injected.

        Args:
            rate: Tokens per second
            capacity: Maximum bucket capacity (defaults to rate)

        Returns:
            Configured rate limiter instance
        """
        resolved_capacity = capacity if capacity is not None else max(1.0, rate)
        return TokenBucketRateLimiterImpl(
            rate=rate,
            capacity=resolved_capacity,
            logger=self.get_logger(),
        )


# Module-level singleton for convenience (can be replaced in tests)
_default_root: CompositionRoot | None = None


def get_composition_root() -> CompositionRoot:
    """
    Get the default composition root singleton.

    For testing, create a new CompositionRoot with mock dependencies instead.
    """
    global _default_root
    if _default_root is None:
        _default_root = CompositionRoot()
    return _default_root


def reset_composition_root() -> None:
    """Reset the default composition root (useful for tests)."""
    global _default_root
    _default_root = None


__all__ = [
    "CompositionRoot",
    "ObservabilityStack",
    "get_composition_root",
    "reset_composition_root",
]
