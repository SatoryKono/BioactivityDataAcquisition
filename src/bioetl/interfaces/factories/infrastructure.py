"""Factory for creating infrastructure components.

Provides abstract factory interface and default implementation for
infrastructure-layer components: config loaders, HTTP transports,
and rate limiters.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.domain.clients.base.contracts import RateLimiterABC
    from bioetl.domain.configs import HttpClientConfig
    from bioetl.domain.configs.contracts import PipelineConfigLoaderProtocol


class InfrastructureFactoryABC(ABC):
    """Abstract factory for infrastructure components."""

    @abstractmethod
    def create_config_loader(self) -> PipelineConfigLoaderProtocol:
        """Create a pipeline configuration loader."""

    @abstractmethod
    def create_rate_limiter(
        self,
        rate: float,
        capacity: float | None = None,
    ) -> RateLimiterABC:
        """Create a rate limiter with specified rate and capacity."""

    @abstractmethod
    def create_http_transport(
        self,
        provider: str,
        config: HttpClientConfig,
        logger: Any,
        metrics: Any,
    ) -> Any:
        """Create an HTTP transport for the specified provider."""


class DefaultInfrastructureFactory(InfrastructureFactoryABC):
    """Default implementation of infrastructure factory."""

    def create_config_loader(self) -> PipelineConfigLoaderProtocol:
        """Create a pipeline configuration loader using bootstrap."""
        from bioetl.application.bootstrap_factory import create_default_bootstrap

        bootstrap = create_default_bootstrap()
        context = bootstrap.start()

        if context.config_loader is None:
            raise RuntimeError("Bootstrap failed to create config_loader")

        return context.config_loader

    def create_rate_limiter(
        self,
        rate: float,
        capacity: float | None = None,
    ) -> RateLimiterABC:
        """Create a rate limiter with token bucket semantics."""
        from bioetl.infrastructure.clients.base.factories import create_rate_limiter

        return create_rate_limiter(rate=rate, capacity=capacity)

    def create_http_transport(
        self,
        provider: str,
        config: HttpClientConfig,
        logger: Any,
        metrics: Any,
    ) -> Any:
        """Create an HTTP transport using build_http_client."""
        from bioetl.infrastructure.clients.base.factories import build_http_client

        return build_http_client(
            provider,
            logger=logger,
            metrics=metrics,
            config=config,
        )


__all__ = ["InfrastructureFactoryABC", "DefaultInfrastructureFactory"]
