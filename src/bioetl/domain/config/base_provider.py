"""Base configuration classes for domain layer.

Consolidates duplicate DTOs by providing base classes with common fields.
Per RULES.md §12.1.6 - "Duplicate DTOs with overlapping fields MUST NOT exist".

This module provides:
- RateLimitConfig: Unified rate limiting configuration
- BaseClientConfig: Base HTTP client configuration
- BaseProviderConfig: Base provider configuration (extends BaseClientConfig)

These classes are frozen dataclasses (Value Objects) with validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "BaseClientConfig",
    "BaseProviderConfig",
    "RateLimitConfig",
]


@dataclass(frozen=True, slots=True)
class RateLimitConfig:
    """Unified rate limiting configuration.

    Consolidates rate limiting fields from:
    - composition/providers/provider_registry.py:HttpConfig
    - infrastructure/schemas/pipeline_config.py:ApiConfig

    Attributes:
        requests_per_second: Maximum requests per second (default: 5.0).
        burst: Token bucket burst capacity (default: 10).

    Example:
        >>> config = RateLimitConfig(requests_per_second=10.0, burst=20)
        >>> config.requests_per_second
        10.0
    """

    requests_per_second: float = 5.0
    burst: int = 10

    def __post_init__(self) -> None:
        """Validate rate limit configuration."""
        self._validate()

    def _validate(self) -> None:
        """Validate rate limit values."""
        if self.requests_per_second <= 0:
            raise ValueError(
                f"requests_per_second must be positive, got {self.requests_per_second}"
            )
        if self.burst < 1:
            raise ValueError(f"burst must be at least 1, got {self.burst}")


@dataclass(frozen=True, slots=True)
class BaseClientConfig:
    """Base HTTP client configuration.

    Provides common fields for HTTP client configurations used by adapters.
    This consolidates fields from:
    - infrastructure/schemas/pipeline_config.py:ApiConfig (base_url, rate_limit, timeout)
    - composition/providers/provider_registry.py:HttpConfig (rate, capacity)

    Attributes:
        base_url: API base URL (optional, provider-specific default).
        timeout: Request timeout in seconds (default: 30).
        rate_limit: Rate limiting configuration.

    Example:
        >>> config = BaseClientConfig(
        ...     base_url="https://api.example.com",
        ...     timeout=60,
        ... )
    """

    base_url: str | None = None
    timeout: int = 30
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)

    def __post_init__(self) -> None:
        """Validate client configuration."""
        self._validate()

    def _validate(self) -> None:
        """Validate configuration values."""
        if self.timeout <= 0:
            raise ValueError(f"timeout must be positive, got {self.timeout}")


@dataclass(frozen=True, slots=True)
class BaseProviderConfig(BaseClientConfig):
    """Base provider configuration.

    Extends BaseClientConfig with provider-specific fields.
    This is the base class for provider-specific configurations like
    ChemblConfig, UniprotConfig, PubchemConfig.

    Attributes:
        base_url: API base URL (inherited).
        timeout: Request timeout in seconds (inherited).
        rate_limit: Rate limiting configuration (inherited).
        batch_size: Number of records per API request (default: 100).
        api_key: Optional API key for authentication.

    Example:
        >>> config = BaseProviderConfig(
        ...     base_url="https://www.ebi.ac.uk/chembl/api/data",
        ...     batch_size=1000,
        ...     rate_limit=RateLimitConfig(requests_per_second=10.0),
        ... )
    """

    batch_size: int = 100
    api_key: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Validate provider configuration."""
        # Call parent validation directly (super() doesn't work with slots=True inheritance)
        BaseClientConfig._validate(self)
        self._validate_provider()

    def _validate_provider(self) -> None:
        """Validate provider-specific values."""
        if self.batch_size <= 0:
            raise ValueError(f"batch_size must be positive, got {self.batch_size}")
