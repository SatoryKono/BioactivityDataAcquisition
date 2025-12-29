"""Factory for creating HTTP clients with standard configurations.

Ensures consistent rate limiting and circuit breaker settings across providers.
Uses source configuration from YAML files (configs/sources/*.yaml) for settings.

Configuration Priority:
1. Source YAML config (configs/sources/{provider}.yaml) - PRIMARY
2. Settings API key overrides (for rate limit boost with API keys)
3. ProviderRegistry defaults (fallback only)

SRP Compliance:
- Creates UnifiedHTTPClient with injected RateLimiterPort and CircuitBreakerPort
- RetryPolicy is configured via domain value object
- Observability components (tracer, metrics, logger) are injected for correlation
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from bioetl.composition.providers import ProviderRegistry, ensure_providers_loaded
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
from bioetl.infrastructure.config import load_source_config

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config import Settings

_logger = logging.getLogger(__name__)


class HttpClientFactory:
    """Factory for creating HTTP clients.

    Uses ProviderRegistry for configuration lookup.
    Injects observability components for distributed tracing and metrics.
    """

    @classmethod
    def create_for_provider(
        cls,
        provider: str,
        settings: Settings | None = None,
        *,
        run_id: RunID | None = None,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        logger: LoggerPort | None = None,
    ) -> UnifiedHTTPClient:
        """Create a configured HTTP client for the given provider.

        Uses ProviderRegistry for configuration lookup.

        Args:
            provider: Provider name (e.g., 'chembl', 'pubmed')
            settings: Optional settings to override defaults (e.g., API keys)
            run_id: Optional run ID for correlation headers
            tracer: Optional TracingPort for distributed tracing
            metrics: Optional MetricsPort for metrics collection
            logger: Optional LoggerPort for structured logging

        Returns:
            UnifiedHTTPClient configured for the provider with observability

        Raises:
            ValueError: If the provider is unknown.
        """
        # Ensure providers are loaded
        ensure_providers_loaded()

        # Validate provider is registered
        if not ProviderRegistry.is_registered(provider):
            available = ", ".join(ProviderRegistry.list_providers())
            raise ValueError(f"Unknown provider: {provider}. Available: {available}")

        return cls._create_from_registry(
            provider,
            settings,
            run_id=run_id,
            tracer=tracer,
            metrics=metrics,
            logger=logger,
        )

    @classmethod
    def _create_from_registry(
        cls,
        provider: str,
        settings: Settings | None,
        *,
        run_id: RunID | None = None,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        logger: LoggerPort | None = None,
    ) -> UnifiedHTTPClient:
        """Create HTTP client using source YAML configuration.

        Configuration is loaded from configs/sources/{provider}.yaml.
        Falls back to ProviderRegistry defaults if source config not found.

        Args:
            provider: Provider name
            settings: Application settings
            run_id: Optional run ID for correlation headers
            tracer: Optional TracingPort for distributed tracing
            metrics: Optional MetricsPort for metrics collection
            logger: Optional LoggerPort for structured logging

        Returns:
            Configured UnifiedHTTPClient with observability
        """
        # Try to load source config from YAML (primary source)
        source_config = None
        try:
            source_config = load_source_config(provider)
        except ValueError:
            _logger.debug(
                "Source config not found for %s, using ProviderRegistry defaults",
                provider,
            )

        # Get rate limit and circuit breaker settings
        if source_config is not None:
            # Use source YAML config (primary)
            rate = source_config.rate_limit.requests_per_second
            capacity = source_config.rate_limit.burst
            failure_threshold = source_config.circuit_breaker.failure_threshold
            recovery_timeout = source_config.circuit_breaker.recovery_timeout
        else:
            # Fallback to ProviderRegistry
            http_config = ProviderRegistry.get_http_config(provider)
            if http_config is None:
                # Provider doesn't use shared HTTP client - use safe defaults
                rate = 5.0
                capacity = 10
                failure_threshold = 5
                recovery_timeout = 300
            else:
                rate = http_config.rate
                capacity = http_config.capacity
                failure_threshold = 5  # Default
                recovery_timeout = 300  # Default

        # Apply rate overrides based on settings (API key boosts)
        http_config = ProviderRegistry.get_http_config(provider)
        if settings and http_config and http_config.rate_overrides:
            for setting_name, override_rate in http_config.rate_overrides.items():
                if cls._check_setting(settings, setting_name):
                    rate = override_rate
                    capacity = int(override_rate * 2)
                    break

        return UnifiedHTTPClient(
            rate_limiter=TokenBucket(rate=rate, capacity=capacity, provider=provider),
            circuit_breaker=CircuitBreaker(
                provider=provider,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                metrics=metrics,
            ),
            provider=provider,
            run_id=run_id,
            tracer=tracer,
            metrics=metrics,
            logger=logger,
        )

    @classmethod
    def _check_setting(cls, settings: Settings, setting_name: str) -> bool:
        """Check if a setting is present and truthy.

        Args:
            settings: Application settings
            setting_name: Name of the setting to check

        Returns:
            True if setting exists and is truthy
        """
        value = getattr(settings, setting_name, None)
        return value is not None and bool(value)
