"""Factory for creating HTTP clients with standard configurations.

Ensures consistent rate limiting and circuit breaker settings across providers.
Uses source configuration from YAML files (configs/providers/*.yaml) for settings.

Configuration Priority:
1. Provider YAML config (configs/providers/{provider}.yaml) - PRIMARY
2. Settings API key overrides (for rate limit boost with API keys)
3. ProviderRegistry defaults (fallback only)

SRP Compliance:
- Creates UnifiedHTTPClient with injected RateLimiterPort and CircuitBreakerPort
- RetryConfig is configured via domain value object
- Observability components (tracer, metrics, logger) are injected for correlation
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.composition.providers.loader import ensure_providers_loaded
from bioetl.composition.providers.provider_registry import ProviderRegistry
from bioetl.domain.resilience import RetryConfig
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter
from bioetl.infrastructure.config import load_source_config

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config import Settings

__all__ = [
    "HttpClientFactory",
    "ResolvedHttpConfig",
]


@dataclass(frozen=True)
class ResolvedHttpConfig:
    """Pure config resolution result — no infrastructure objects.

    Extracted from ``HttpClientFactory._create_from_registry`` so that config
    resolution logic can be tested in isolation without constructing real
    TokenBucketRateLimiter / CircuitBreakerGuard / UnifiedHTTPClient instances.
    """

    rate: float
    capacity: int
    failure_threshold: int
    recovery_timeout: int
    timeout: float
    max_retries: int
    base_delay: float
    max_delay: float
    max_connections: int
    max_keepalive: int


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
    def _resolve_config(
        cls,
        provider: str,
        settings: Settings | None,
    ) -> ResolvedHttpConfig:
        """Pure config resolution — no infrastructure objects created.

        Priority: source YAML > ProviderRegistry > safe defaults.
        API-key rate overrides applied last.

        Args:
            provider: Provider name
            settings: Application settings (used for API-key rate overrides)

        Returns:
            ResolvedHttpConfig with all scalar values resolved.
        """
        # Load source config from provider YAML (primary source) if exists.
        try:
            source_config = load_source_config(provider)
        except ValueError:
            source_config = None

        if source_config is not None:
            rate = source_config.rate_limit.requests_per_second
            capacity = source_config.rate_limit.burst
            failure_threshold = source_config.circuit_breaker.failure_threshold
            recovery_timeout = source_config.circuit_breaker.recovery_timeout
            timeout = source_config.timeout_sec
            max_retries = source_config.max_retries
            base_delay = source_config.retry_base_delay
            max_delay = source_config.retry_max_delay
            max_connections = source_config.max_connections
            max_keepalive = source_config.max_keepalive_connections
        else:
            # Fallback defaults when no source YAML config is available
            _FALLBACK_TIMEOUT = 30.0
            _FALLBACK_MAX_RETRIES = 3
            _FALLBACK_CB_THRESHOLD = 5
            _FALLBACK_CB_RECOVERY = 300
            http_config = ProviderRegistry.get_http_config(provider)
            if http_config is None:
                rate, capacity = 5.0, 10
                failure_threshold, recovery_timeout = _FALLBACK_CB_THRESHOLD, _FALLBACK_CB_RECOVERY
                timeout, max_retries = _FALLBACK_TIMEOUT, _FALLBACK_MAX_RETRIES
            else:
                rate, capacity = http_config.rate, http_config.capacity
                failure_threshold, recovery_timeout = _FALLBACK_CB_THRESHOLD, _FALLBACK_CB_RECOVERY
                timeout, max_retries = _FALLBACK_TIMEOUT, _FALLBACK_MAX_RETRIES
            base_delay, max_delay = 1.0, 60.0
            max_connections, max_keepalive = 50, 10

        # Apply rate overrides based on settings (API key boosts)
        http_config = ProviderRegistry.get_http_config(provider)
        if settings and http_config and http_config.rate_overrides:
            for setting_name, override_rate in http_config.rate_overrides.items():
                if cls._check_setting(settings, setting_name):
                    rate = override_rate
                    capacity = int(override_rate * 2)
                    break

        return ResolvedHttpConfig(
            rate=rate,
            capacity=capacity,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            timeout=timeout,
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
            max_connections=max_connections,
            max_keepalive=max_keepalive,
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
        """Thin assembler: resolves config, then constructs infrastructure objects.

        Args:
            provider: Provider name used as label in HTTP client configuration.
            settings: Optional application settings for API-key rate overrides.
            run_id: Optional run ID for correlation headers; defaults to None.
            tracer: Optional TracingPort for distributed tracing; defaults to None.
            metrics: Optional MetricsPort for circuit breaker metrics; defaults to None.
            logger: Optional LoggerPort for HTTP client logging; defaults to None.

        Returns:
            Configured UnifiedHTTPClient with rate limiter and circuit breaker.
        """
        cfg = cls._resolve_config(provider, settings)

        return UnifiedHTTPClient(
            rate_limiter=TokenBucketRateLimiter(
                rate=cfg.rate, capacity=cfg.capacity, provider=provider
            ),
            circuit_breaker=CircuitBreakerGuard(
                provider=provider,
                failure_threshold=cfg.failure_threshold,
                recovery_timeout=cfg.recovery_timeout,
                metrics=metrics,
            ),
            retry_config=RetryConfig(
                max_attempts=cfg.max_retries,
                base_delay=cfg.base_delay,
                max_delay=cfg.max_delay,
            ),
            timeout=cfg.timeout,
            provider=provider,
            run_id=run_id,
            max_connections=cfg.max_connections,
            max_keepalive_connections=cfg.max_keepalive,
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
