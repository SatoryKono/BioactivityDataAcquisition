"""Factory for creating HTTP clients with standard configurations.

Ensures consistent rate limiting and circuit breaker settings across providers.
Uses ProviderRegistry for unified configuration management.

SRP Compliance:
- Creates UnifiedHTTPClient with injected RateLimiterPort and CircuitBreakerPort
- RetryPolicy is configured via domain value object
- Observability components (tracer, metrics, logger) are injected for correlation

Configuration Priority:
1. Pipeline-specific config from YAML (source.rate_limit, source.circuit_breaker)
2. Provider defaults from ProviderRegistry (HttpConfig)
3. Fallback defaults (rate=5.0, capacity=10, failure_threshold=5, recovery_timeout=300)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.providers import ProviderRegistry, ensure_providers_loaded
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


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
        pipeline_config: PipelineYamlConfig | None = None,
        run_id: RunID | None = None,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        logger: LoggerPort | None = None,
    ) -> UnifiedHTTPClient:
        """Create a configured HTTP client for the given provider.

        Uses pipeline_config for rate limits and circuit breaker settings,
        falling back to ProviderRegistry defaults if not specified.

        Args:
            provider: Provider name (e.g., 'chembl', 'pubmed')
            settings: Optional settings to override defaults (e.g., API keys)
            pipeline_config: Optional pipeline config with source-specific settings.
                If provided, uses source.rate_limit and source.circuit_breaker.
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
            pipeline_config=pipeline_config,
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
        pipeline_config: PipelineYamlConfig | None = None,
        run_id: RunID | None = None,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        logger: LoggerPort | None = None,
    ) -> UnifiedHTTPClient:
        """Create HTTP client using configuration from pipeline config and registry.

        Configuration priority:
        1. Pipeline-specific config (source.rate_limit, source.circuit_breaker)
        2. Provider defaults from ProviderRegistry (HttpConfig)
        3. Fallback defaults

        Args:
            provider: Provider name
            settings: Application settings
            pipeline_config: Optional pipeline config with source-specific settings
            run_id: Optional run ID for correlation headers
            tracer: Optional TracingPort for distributed tracing
            metrics: Optional MetricsPort for metrics collection
            logger: Optional LoggerPort for structured logging

        Returns:
            Configured UnifiedHTTPClient with observability
        """
        # Get circuit breaker settings from pipeline config or use defaults
        failure_threshold = 5
        recovery_timeout = 300

        if pipeline_config:
            # Use source.circuit_breaker from configs/sources/*.yaml
            source_cb = pipeline_config.source.circuit_breaker
            failure_threshold = source_cb.failure_threshold
            recovery_timeout = source_cb.recovery_timeout

        # Get rate limit settings
        rate: float = 5.0
        capacity: int = 10

        if pipeline_config:
            # Use source.rate_limit from configs/sources/*.yaml
            source_rl = pipeline_config.source.rate_limit
            rate = source_rl.requests_per_second
            capacity = source_rl.burst

        # Check ProviderRegistry for rate overrides based on settings (e.g., API key)
        http_config = ProviderRegistry.get_http_config(provider)

        if http_config is not None and settings and http_config.rate_overrides:
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
