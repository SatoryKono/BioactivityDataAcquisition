"""Read back non-secret production settings before live acceptance launches."""

from __future__ import annotations

import json

from bioetl.composition.factories.datasource.http_client import HttpClientFactory
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter
from bioetl.infrastructure.config.config_root import resolve_config_subdir
from bioetl.infrastructure.config.settings_api import get_settings
from bioetl.infrastructure.control_plane._durability import (
    should_fsync_control_plane_writes,
)


def runtime_policy() -> dict:
    """Reject test-mode contamination and expose only an explicit safe allowlist."""
    settings = get_settings()
    fsync = should_fsync_control_plane_writes()
    if settings.test_mode or not fsync:
        raise ValueError("live_acceptance_requires_production_runtime")
    providers = {}
    for path in sorted(resolve_config_subdir("providers").glob("*.yaml")):
        client = HttpClientFactory.create_for_provider(path.stem, settings)
        if not isinstance(client.rate_limiter, TokenBucketRateLimiter):
            raise TypeError("live_acceptance_rate_limiter_not_inspectable")
        providers[path.stem] = {
            "timeout_seconds": client.timeout,
            "read_timeout_seconds": client.timeout * client.read_timeout_multiplier,
            "max_attempts": client.retry_config.max_attempts,
            "retry_base_delay_seconds": client.retry_config.base_delay,
            "retry_max_delay_seconds": client.retry_config.max_delay,
            "retry_after_cap_seconds": client.retry_config.max_retry_after_seconds,
            "rate_per_second": client.rate_limiter.rate,
            "burst": client.rate_limiter.capacity,
            "circuit_recovery_seconds": client.circuit_breaker.get_recovery_timeout(),
        }
    return {
        "test_mode": settings.test_mode,
        "control_plane_fsync": fsync,
        "providers": providers,
    }


if __name__ == "__main__":
    print(json.dumps(runtime_policy(), sort_keys=True))
