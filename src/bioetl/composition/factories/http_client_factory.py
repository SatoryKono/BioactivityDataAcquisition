"""Factory for creating HTTP clients with standard configurations.

Ensures consistent rate limiting and circuit breaker settings across providers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket

if TYPE_CHECKING:
    from bioetl.infrastructure.config import Settings


class HttpClientFactory:
    """Factory for creating HTTP clients."""

    # Default configurations per provider
    PROVIDER_CONFIGS: dict[str, dict[str, Any]] = {
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

        Args:
            provider: Provider name (e.g., 'chembl', 'pubmed')
            settings: Optional settings to override defaults (e.g., API keys)

        Returns:
            UnifiedHTTPClient
        """
        config = cls.PROVIDER_CONFIGS.get(provider, {"rate": 5.0, "capacity": 10})
        rate = config["rate"]
        capacity = config["capacity"]

        # Specific overrides based on settings
        if provider == "pubmed" and settings and settings.pubmed_api_key:
            rate = 10.0
            capacity = 20

        if provider == "uniprot" and settings and getattr(settings, "uniprot_api_key", None):
             # Hypothetical override if uniprot key is in settings
             rate = 100.0
             capacity = 200

        return UnifiedHTTPClient(
            rate_limiter=TokenBucket(rate=rate, capacity=capacity),
            circuit_breaker=CircuitBreaker(provider=provider),
        )
