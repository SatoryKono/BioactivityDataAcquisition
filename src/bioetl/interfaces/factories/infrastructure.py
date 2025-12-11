"""Factory for creating infrastructure components.

Provides abstract factory interface and default implementation for
infrastructure-layer components: config loaders, HTTP transports,
rate limiters, metadata builders, and validator factories.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from bioetl.domain.clients.base.contracts import RateLimiterABC
    from bioetl.domain.clients.base.output.contracts import RunMetadataBuilderProtocol
    from bioetl.domain.configs import HttpClientConfig
    from bioetl.domain.configs.contracts import PipelineConfigLoaderProtocol
    from bioetl.domain.observability import LoggingPortABC, MetricsPortABC
    from bioetl.domain.validation import ValidatorFactoryABC


class InfrastructureFactoryABC(ABC):
    """Abstract factory for infrastructure components."""

    @abstractmethod
    def create_config_loader(self) -> PipelineConfigLoaderProtocol:
        """Create pipeline config loader."""

    @abstractmethod
    def create_rate_limiter(
        self,
        logger: LoggingPortABC,
        rate: float,
        capacity: float | None = None,
    ) -> RateLimiterABC:
        """Create rate limiter instance."""

    @abstractmethod
    def create_http_transport(
        self,
        provider: str,
        config: HttpClientConfig,
        logger: LoggingPortABC,
        metrics: MetricsPortABC,
        base_client: Any | None = None,
    ) -> Any:
        """Create HTTP transport with dependencies."""

    @abstractmethod
    def create_metadata_builder(self) -> RunMetadataBuilderProtocol:
        """Create run metadata builder."""

    @abstractmethod
    def create_validator_factory(self) -> ValidatorFactoryABC:
        """Create validator factory."""


class DefaultInfrastructureFactory(InfrastructureFactoryABC):
    """Default factory using infrastructure implementations."""

    def __init__(self) -> None:
        self._registry_resolver: Any | None = None

    def create_config_loader(self) -> PipelineConfigLoaderProtocol:
        """Create a pipeline configuration loader using bootstrap."""
        from bioetl.application.bootstrap_factory import create_default_bootstrap

        bootstrap = create_default_bootstrap()
        context = bootstrap.start()

        if context.config_loader is None:
            raise RuntimeError("Config loader not available")
        return context.config_loader

    def create_rate_limiter(
        self,
        logger: LoggingPortABC,
        rate: float,
        capacity: float | None = None,
    ) -> RateLimiterABC:
        """Create a rate limiter with token bucket semantics."""
        from bioetl.infrastructure.clients.base.factories import (
            create_rate_limiter as infra_create_rate_limiter,
        )

        return infra_create_rate_limiter(logger=logger, rate=rate, capacity=capacity)

    def create_http_transport(
        self,
        provider: str,
        config: HttpClientConfig,
        logger: LoggingPortABC,
        metrics: MetricsPortABC,
        base_client: Any | None = None,
    ) -> Any:
        """Create an HTTP transport using build_http_client."""
        import requests

        from bioetl.infrastructure.clients.base.factories import build_http_client

        return build_http_client(
            provider=provider,
            logger=logger,
            metrics=metrics,
            config=config,
            base_client=base_client or requests.Session(),
        )

    def create_metadata_builder(self) -> RunMetadataBuilderProtocol:
        """Create run metadata builder using SimpleNamespace."""
        from bioetl.infrastructure.output.metadata import (
            build_dry_run_metadata,
            build_run_metadata,
        )

        return cast(
            RunMetadataBuilderProtocol,
            SimpleNamespace(
                build_run_metadata=build_run_metadata,
                build_dry_run_metadata=build_dry_run_metadata,
            ),
        )

    def create_validator_factory(self) -> ValidatorFactoryABC:
        """Create validator factory via registry resolver."""
        resolver = self._get_registry_resolver()
        factory = resolver.resolve_default_factory("ValidatorFactoryABC")
        return factory()

    def _get_registry_resolver(self) -> Any:
        """Lazy-load ABCRegistryResolver."""
        if self._registry_resolver is None:
            from bioetl.infrastructure.clients.base.abc_registry_resolver import (
                ABCRegistryResolver,
            )

            self._registry_resolver = ABCRegistryResolver()
        return self._registry_resolver


__all__ = [
    "InfrastructureFactoryABC",
    "DefaultInfrastructureFactory",
]
