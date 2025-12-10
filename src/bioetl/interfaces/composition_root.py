"""
Composition Root for assembling the application's dependency graph.

This module is the single place where concrete implementations are instantiated
and wired together. No other module should create dependencies with default fallbacks.

Usage:
    # For production:
    root = CompositionRoot()
    http_transport = root.create_http_transport(provider="chembl", config=http_config)
    loader = root.create_schema_contract_loader()

    # For testing:
    root = CompositionRoot(
        logger=mock_logger,
        metrics=mock_metrics,
        schema_contract_provider=mock_provider,
    )
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import requests

from bioetl.domain.clients.base.contracts import RateLimiterABC
from bioetl.domain.configs import HttpClientConfig
from bioetl.domain.observability import LoggingPortABC, MetricsPortABC
from bioetl.domain.ports.schema import SchemaContractProviderABC
from bioetl.infrastructure.clients.base.factories import (
    build_http_client,
    default_rate_limiter,
)
from bioetl.infrastructure.observability.factories import (
    default_logging_port,
    default_metrics_port,
)

if TYPE_CHECKING:
    from bioetl.infrastructure.config.loader import SchemaContractLoader


@dataclass(frozen=True)
class ObservabilityStack:
    """Container for observability dependencies."""

    logger: LoggingPortABC
    metrics: MetricsPortABC


class CompositionRoot:
    """
    Central factory for creating application components.

    Ensures proper dependency injection. The composition root is the only
    place where default implementations are created.
    All other modules receive their dependencies explicitly.

    Example:
        >>> root = CompositionRoot()
        >>> transport = root.create_http_transport("chembl", HttpClientConfig())
        >>> loader = root.create_schema_contract_loader()

        # For testing with mocks:
        >>> root = CompositionRoot(
        ...     logger=mock_logger,
        ...     metrics=mock_metrics,
        ...     schema_contract_provider=mock_provider,
        ... )
        >>> transport = root.create_http_transport("chembl", HttpClientConfig())
    """

    def __init__(
        self,
        *,
        logger: LoggingPortABC | None = None,
        metrics: MetricsPortABC | None = None,
        http_session_factory: type | None = None,
        schema_contract_provider: SchemaContractProviderABC | None = None,
    ) -> None:
        """
        Initialize composition root with optional overrides.

        Args:
            logger: Custom logger implementation (defaults to structured logger)
            metrics: Custom metrics implementation (defaults to Prometheus)
            http_session_factory: Factory for HTTP sessions
                (defaults to requests.Session)
            schema_contract_provider: Custom schema contract provider
                (defaults to bootstrapped provider from schema registry)
        """
        self._logger = logger
        self._metrics = metrics
        self._http_session_factory = http_session_factory or requests.Session
        self._schema_contract_provider = schema_contract_provider

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
    ) -> Any:
        """
        Create an HTTP transport with all dependencies injected.

        Args:
            provider: Provider identifier (e.g., "chembl")
            config: HTTP client configuration
            base_client: Optional pre-configured HTTP client

        Returns:
            Fully configured HTTP transport instance
        """
        return build_http_client(
            provider=provider,
            logger=self.get_logger(),
            metrics=self.get_metrics(),
            config=config,
            base_client=base_client or self.create_http_session(),
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
        return default_rate_limiter(
            logger=self.get_logger(),
            rate=rate,
            capacity=capacity,
        )

    def get_schema_contract_provider(self) -> SchemaContractProviderABC:
        """Get or create the schema contract provider instance.

        If not provided during initialization, creates a default provider
        by bootstrapping the schema registry.

        Returns:
            Configured SchemaContractProviderABC instance.
        """
        if self._schema_contract_provider is None:
            self._schema_contract_provider = _create_default_schema_contract_provider()
        return self._schema_contract_provider

    def create_schema_contract_loader(self) -> "SchemaContractLoader":
        """Create a SchemaContractLoader with the configured provider.

        This is the preferred method for obtaining a configuration loader
        with proper dependency injection.

        Returns:
            SchemaContractLoader with injected schema contract provider.

        Example:
            >>> root = CompositionRoot()
            >>> loader = root.create_schema_contract_loader()
            >>> config = loader.get_pipeline_config("chembl.activity")
        """
        from bioetl.infrastructure.config.loader import SchemaContractLoader

        return SchemaContractLoader(self.get_schema_contract_provider())


def _create_default_schema_contract_provider() -> SchemaContractProviderABC:
    """Create default schema contract provider by bootstrapping schema registry.

    This function is called lazily when no provider is explicitly configured.

    Returns:
        Configured SchemaContractProviderImpl instance.
    """
    from bioetl.application.services.schema_bootstrap import (
        create_schema_bootstrap_service,
    )
    from bioetl.application.services.schema_contract_provider import (
        SchemaContractProviderImpl,
    )

    schema_service = create_schema_bootstrap_service()
    schema_provider = schema_service.ensure_registered()
    return SchemaContractProviderImpl(schema_provider)


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
