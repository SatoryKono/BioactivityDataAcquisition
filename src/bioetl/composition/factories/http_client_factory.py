"""Factory for creating HTTP clients with standard configurations.

Ensures consistent rate limiting and circuit breaker settings across providers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket

if TYPE_CHECKING:
    from bioetl.infrastructure.config import Settings


class HttpClientFactory:
    """Factory for creating HTTP clients."""

    # Default configurations per provider
    PROVIDER_CONFIGS: ClassVar[dict[str, dict[str, Any]]] = {
        "chembl": {"rate": 10.0, "capacity": 20},
        "pubchem": {"rate": 5.0, "capacity": 10},
        "uniprot": {"rate": 10.0, "capacity": 20},
        "pubmed": {"rate": 3.0, "capacity": 6},
    }

    @classmethod
    def create_for_provider(
        cls,
        provider: str,
        settings: Settings | None = None,
        config: dict[str, Any] | None = None,
    ) -> UnifiedHTTPClient:
        """Create a configured HTTP client for the given provider.

        Prioritizes configuration sources:
        1. Passed config dictionary (from YAML)
        2. Settings (environment variables/secrets)
        3. Hardcoded defaults

        Args:
            provider: Provider name (e.g., 'chembl', 'pubmed')
            settings: Optional settings to override defaults (e.g., API keys)
            config: Optional configuration dictionary (e.g. from pipeline YAML)

        Returns:
            UnifiedHTTPClient
        """
        defaults = cls.PROVIDER_CONFIGS.get(provider, {"rate": 5.0, "capacity": 10})
        rate = float(defaults["rate"])
        capacity = int(defaults["capacity"])

        # Override from settings (Env vars/Secrets)
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

        # Override from specific config (YAML) - Highest priority
        if config:
            rate_limit_config = config.get("rate_limit", {})
            if "requests_per_second" in rate_limit_config:
                rate = float(rate_limit_config["requests_per_second"])
            if "burst" in rate_limit_config:
                capacity = int(rate_limit_config["burst"])

        return UnifiedHTTPClient(
            rate_limiter=TokenBucket(rate=rate, capacity=capacity),
            circuit_breaker=CircuitBreaker(provider=provider),
        )
