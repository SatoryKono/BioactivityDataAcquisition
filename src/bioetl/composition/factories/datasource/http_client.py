"""Factory for provider-specific HTTP clients."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.composition.factories.datasource.provider_registry_resolution import (
    resolve_datasource_provider_registry as _resolve_provider_registry,
)
from bioetl.composition.providers.provider_registry import (
    ProviderDataSourceAccessProtocol,
)
from bioetl.domain.resilience import RetryConfig
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter
from bioetl.infrastructure.config.source_config_loader import load_source_config

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config._base import Settings

__all__ = [
    "HttpClientFactory",
    "ResolvedHttpConfig",
]


@dataclass(frozen=True)
class ResolvedHttpConfig:
    """Resolved HTTP scalar config."""

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
    trust_env: bool


class HttpClientFactory:
    """Create HTTP clients from source config plus registry fallbacks."""

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
        provider_registry: ProviderDataSourceAccessProtocol | None = None,
    ) -> UnifiedHTTPClient:
        """Create a configured client for ``provider``."""
        registry = _resolve_provider_registry(provider_registry)
        if not registry.is_registered(provider):
            available = ", ".join(registry.list_providers())
            raise ValueError(f"Unknown provider: {provider}. Available: {available}")

        return cls._create_from_registry(
            provider,
            settings,
            run_id=run_id,
            tracer=tracer,
            metrics=metrics,
            logger=logger,
            provider_registry=registry,
        )

    @classmethod
    def _resolve_config(
        cls,
        provider: str,
        settings: Settings | None,
        *,
        provider_registry: ProviderDataSourceAccessProtocol | None = None,
    ) -> ResolvedHttpConfig:
        """Resolve scalar config from source YAML, registry, and overrides."""
        registry = _resolve_provider_registry(provider_registry)
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
            trust_env = source_config.trust_env
        else:
            _FALLBACK_TIMEOUT = 30.0
            _FALLBACK_MAX_RETRIES = 3
            _FALLBACK_CB_THRESHOLD = 5
            _FALLBACK_CB_RECOVERY = 300
            http_config = registry.get_http_config(provider)
            if http_config is None:
                rate, capacity = 5.0, 10
                failure_threshold, recovery_timeout = (
                    _FALLBACK_CB_THRESHOLD,
                    _FALLBACK_CB_RECOVERY,
                )
                timeout, max_retries = _FALLBACK_TIMEOUT, _FALLBACK_MAX_RETRIES
            else:
                rate, capacity = http_config.rate, http_config.capacity
                failure_threshold, recovery_timeout = (
                    _FALLBACK_CB_THRESHOLD,
                    _FALLBACK_CB_RECOVERY,
                )
                timeout, max_retries = _FALLBACK_TIMEOUT, _FALLBACK_MAX_RETRIES
            base_delay, max_delay = 1.0, 60.0
            max_connections, max_keepalive = 50, 10
            trust_env = True

        http_config = registry.get_http_config(provider)
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
            trust_env=trust_env,
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
        provider_registry: ProviderDataSourceAccessProtocol | None = None,
    ) -> UnifiedHTTPClient:
        """Resolve config and assemble a ``UnifiedHTTPClient``."""
        cfg = cls._resolve_config(
            provider,
            settings,
            provider_registry=provider_registry,
        )

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
            trust_env=cfg.trust_env,
            tracer=tracer,
            metrics=metrics,
            logger=logger,
        )

    @classmethod
    def _check_setting(cls, settings: Settings, setting_name: str) -> bool:
        """Return ``True`` when the setting exists and is truthy."""
        value = getattr(settings, setting_name, None)
        return value is not None and bool(value)
