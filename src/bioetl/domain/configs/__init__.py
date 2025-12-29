"""Domain configuration base classes.

This module provides base configuration classes for common configuration patterns.
It consolidates duplicate DTOs per RULES.md §12.1.6 - "Дублирующие DTO с
пересекающимися полями MUST NOT".

Consolidated Classes:
- RateLimitConfig: Rate limiting configuration (requests/second, burst)
- BaseClientConfig: Base HTTP client configuration
- BaseProviderConfig: Base provider configuration with common fields

Usage:
    from bioetl.domain.configs import RateLimitConfig, BaseProviderConfig

    config = BaseProviderConfig(
        base_url="https://api.example.com",
        timeout=30,
        rate_limit=RateLimitConfig(requests_per_second=5.0, burst=10),
    )
"""

from bioetl.domain.configs.base import (
    BaseClientConfig,
    BaseProviderConfig,
    RateLimitConfig,
)

__all__ = [
    "BaseClientConfig",
    "BaseProviderConfig",
    "RateLimitConfig",
]
