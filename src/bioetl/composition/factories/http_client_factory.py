"""Factory for creating HTTP clients with standard configurations.

Ensures consistent rate limiting and circuit breaker settings across providers.
Uses ProviderRegistry for unified configuration management.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from bioetl.composition.providers import ProviderRegistry, ensure_providers_loaded
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket

if TYPE_CHECKING:
    from bioetl.infrastructure.config import Settings


class HttpClientFactory:
    """Factory for creating HTTP clients.

    Uses ProviderRegistry for configuration lookup.
    Falls back to legacy static mapping for backward compatibility.
    """

    # Legacy configurations for backward compatibility
    # Will be removed after full migration to ProviderRegistry
    PROVIDER_CONFIGS: ClassVar[dict[str, dict[str, Any]]] = {
        "chembl": {"rate": 10.0, "capacity": 20},
        "pubchem": {"rate": 5.0, "capacity": 10},
        "uniprot": {"rate": 10.0, "capacity": 20},
        "pubmed": {"rate": 3.0, "capacity": 6},
    }

    @classmethod
    def create_for_provider(
        cls, provider: str, settings: Settings | None = None
    ) -> UnifiedHTTPClient:
        """Create a configured HTTP client for the given provider.

        First attempts to use ProviderRegistry for configuration.
        Falls back to legacy static mapping if provider not found.

        Args:
            provider: Provider name (e.g., 'chembl', 'pubmed')
            settings: Optional settings to override defaults (e.g., API keys)

        Returns:
            UnifiedHTTPClient configured for the provider
        """
        # Ensure providers are loaded
        ensure_providers_loaded()

        # Try ProviderRegistry first
        if ProviderRegistry.is_registered(provider):
            return cls._create_from_registry(provider, settings)

        # Legacy fallback
        return cls._create_legacy(provider, settings)

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

    @classmethod
    def _create_legacy(
        cls, provider: str, settings: Settings | None
    ) -> UnifiedHTTPClient:
        """Legacy HTTP client creation.

        Used for backward compatibility with providers not yet migrated
        to ProviderRegistry.

        Args:
            provider: Provider name
            settings: Application settings

        Returns:
            Configured UnifiedHTTPClient
        """
        config = cls.PROVIDER_CONFIGS.get(provider, {"rate": 5.0, "capacity": 10})
        rate = config["rate"]
        capacity = config["capacity"]

        # Specific overrides based on settings
        if provider == "pubmed" and settings and settings.pubmed_api_key:
            rate = 10.0
            capacity = 20

        if (
            provider == "uniprot"
            and settings
            and getattr(settings, "uniprot_api_key", None)
        ):
            rate = 100.0
            capacity = 200

        return UnifiedHTTPClient(
            rate_limiter=TokenBucket(rate=rate, capacity=capacity),
            circuit_breaker=CircuitBreaker(provider=provider),
        )
