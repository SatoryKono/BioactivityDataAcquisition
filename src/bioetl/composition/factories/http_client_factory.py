"""Factory for creating HTTP clients with standard configurations.

Ensures consistent rate limiting and circuit breaker settings across providers.
Uses ProviderRegistry for unified configuration management.

SRP Compliance:
- Creates UnifiedHTTPClient with injected RateLimiterPort and CircuitBreakerPort
- RetryPolicy is configured via domain value object
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.providers import ProviderRegistry, ensure_providers_loaded
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket

if TYPE_CHECKING:
    from bioetl.infrastructure.config import Settings


class HttpClientFactory:
    """Factory for creating HTTP clients.

    Uses ProviderRegistry for configuration lookup.
    """

    @classmethod
    def create_for_provider(
        cls, provider: str, settings: Settings | None = None
    ) -> UnifiedHTTPClient:
        """Create a configured HTTP client for the given provider.

        Uses ProviderRegistry for configuration lookup.

        Args:
            provider: Provider name (e.g., 'chembl', 'pubmed')
            settings: Optional settings to override defaults (e.g., API keys)

        Returns:
            UnifiedHTTPClient configured for the provider

        Raises:
            ValueError: If the provider is unknown.
        """
        # Ensure providers are loaded
        ensure_providers_loaded()

        # Validate provider is registered
        if not ProviderRegistry.is_registered(provider):
            available = ", ".join(ProviderRegistry.list_providers())
            raise ValueError(f"Unknown provider: {provider}. Available: {available}")

        return cls._create_from_registry(provider, settings)

    @classmethod
    def _create_from_registry(
        cls, provider: str, settings: Settings | None
    ) -> UnifiedHTTPClient:
        """Create HTTP client using ProviderRegistry configuration.

        Args:
            provider: Provider name
            settings: Application settings

        Returns:
            Configured UnifiedHTTPClient
        """
        http_config = ProviderRegistry.get_http_config(provider)

        if http_config is None:
            # Provider doesn't use shared HTTP client
            # Return default client
            return UnifiedHTTPClient(
                rate_limiter=TokenBucket(rate=5.0, capacity=10),
                circuit_breaker=CircuitBreaker(provider=provider),
            )

        rate = http_config.rate
        capacity = http_config.capacity

        # Apply rate overrides based on settings
        if settings and http_config.rate_overrides:
            for setting_name, override_rate in http_config.rate_overrides.items():
                if cls._check_setting(settings, setting_name):
                    rate = override_rate
                    capacity = int(override_rate * 2)
                    break

        return UnifiedHTTPClient(
            rate_limiter=TokenBucket(rate=rate, capacity=capacity),
            circuit_breaker=CircuitBreaker(provider=provider),
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
