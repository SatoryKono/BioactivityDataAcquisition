"""Schema validation for source configuration.

Implements strict validation for source YAML configurations (configs/sources/*.yaml).
These configs define provider-specific settings like rate limits, circuit breaker,
and batch sizes that were previously hardcoded.

Usage:
    >>> from bioetl.infrastructure.schemas.source_config import SourceYamlConfig
    >>> config = SourceYamlConfig.model_validate(yaml_data)
    >>> rate_limit = config.source.rate_limit.requests_per_second
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from bioetl.domain.resilience import AdapterConfig as DomainAdapterConfig
from bioetl.domain.resilience import CircuitBreakerConfig as DomainCircuitBreakerConfig


class RateLimitYamlConfig(BaseModel):
    """Rate limit configuration from YAML.

    Attributes:
        requests_per_second: Maximum requests per second.
        burst: Maximum burst capacity (token bucket).
    """

    model_config = ConfigDict(extra="ignore")

    requests_per_second: float = Field(default=5.0, ge=0.1, le=100.0)
    burst: int = Field(default=10, ge=1, le=200)


class CircuitBreakerYamlConfig(BaseModel):
    """Circuit breaker configuration from YAML.

    Attributes:
        failure_threshold: Number of consecutive failures before opening circuit.
        recovery_timeout: Time in seconds before attempting recovery.
    """

    model_config = ConfigDict(extra="ignore")

    failure_threshold: int = Field(default=5, ge=1, le=20)
    recovery_timeout: int = Field(default=300, ge=60, le=3600)

    def to_domain(self) -> DomainCircuitBreakerConfig:
        """Convert to domain CircuitBreakerConfig dataclass.

        Returns:
            DomainCircuitBreakerConfig: Immutable domain configuration.
        """
        return DomainCircuitBreakerConfig(
            failure_threshold=self.failure_threshold,
            recovery_timeout=self.recovery_timeout,
        )


class ClientYamlConfig(BaseModel):
    """HTTP client configuration from YAML.

    Attributes:
        timeout_sec: Request timeout in seconds.
        max_retries: Maximum number of retry attempts.
    """

    model_config = ConfigDict(extra="ignore")

    timeout_sec: float = Field(default=30.0, ge=1.0, le=300.0)
    max_retries: int = Field(default=3, ge=0, le=10)


class ProviderConfigYaml(BaseModel):
    """Provider-specific configuration from YAML.

    Attributes:
        provider: Provider name (chembl, pubchem, uniprot, pubmed).
        base_url: Base URL for the API.
        client: HTTP client settings.
        batch_size: Provider-specific batch size for API requests.
        page_size: Page size for paginated requests (ChEMBL specific).
        max_url_length: Maximum URL length (ChEMBL specific).
        default_email: Default email for NCBI APIs (PubMed specific).
    """

    model_config = ConfigDict(extra="ignore")

    provider: str = ""
    base_url: str | None = None
    client: ClientYamlConfig = Field(default_factory=ClientYamlConfig)
    batch_size: int | None = Field(default=None, ge=1, le=10000)
    page_size: int | None = Field(default=None, ge=1, le=10000)
    max_url_length: int | None = Field(default=None, ge=100, le=10000)
    api_version: str | None = None
    default_email: str | None = None


class SourceSectionConfig(BaseModel):
    """Source section configuration from YAML.

    This represents the 'source' section in configs/sources/*.yaml files.

    Attributes:
        type: Source type (api, file, etc).
        load_strategy: Loading strategy (full, incremental).
        batch_size: Batch size for data loading.
        provider_config: Provider-specific settings.
        circuit_breaker: Circuit breaker configuration.
        rate_limit: Rate limiting configuration.
    """

    model_config = ConfigDict(extra="ignore")

    type: Literal["api", "file"] = "api"
    load_strategy: Literal["full", "incremental"] = "full"
    batch_size: int = Field(default=100, ge=1, le=10000)
    provider_config: ProviderConfigYaml = Field(
        default_factory=lambda: ProviderConfigYaml()
    )
    circuit_breaker: CircuitBreakerYamlConfig = Field(
        default_factory=lambda: CircuitBreakerYamlConfig()
    )
    rate_limit: RateLimitYamlConfig = Field(
        default_factory=lambda: RateLimitYamlConfig()
    )


class SourceYamlConfig(BaseModel):
    """Root schema for source configuration files.

    Validates configs/sources/*.yaml files.

    Example YAML:
        source:
            type: api
            batch_size: 100
            provider_config:
                provider: chembl
                base_url: https://www.ebi.ac.uk/chembl/api/data
            circuit_breaker:
                failure_threshold: 5
                recovery_timeout: 300
            rate_limit:
                requests_per_second: 5.0
                burst: 10
    """

    model_config = ConfigDict(extra="ignore")

    source: SourceSectionConfig = Field(default_factory=SourceSectionConfig)

    @property
    def provider_config(self) -> ProviderConfigYaml:
        """Get provider config from nested source config.

        Convenience property for consistent API access.
        """
        return self.source.provider_config

    @property
    def provider(self) -> str:
        """Get provider name from nested config."""
        return self.source.provider_config.provider

    @property
    def rate_limit(self) -> RateLimitYamlConfig:
        """Get rate limit config."""
        return self.source.rate_limit

    @property
    def circuit_breaker(self) -> CircuitBreakerYamlConfig:
        """Get circuit breaker config."""
        return self.source.circuit_breaker

    @property
    def batch_size(self) -> int:
        """Get batch size (provider_config takes precedence over source level)."""
        if self.source.provider_config.batch_size is not None:
            return self.source.provider_config.batch_size
        return self.source.batch_size

    @property
    def page_size(self) -> int | None:
        """Get page size for paginated APIs (e.g., ChEMBL).

        Returns None if not specified, allowing adapters to use their defaults.
        """
        return self.source.provider_config.page_size

    @property
    def timeout_sec(self) -> float:
        """Get timeout in seconds."""
        return self.source.provider_config.client.timeout_sec

    @property
    def max_retries(self) -> int:
        """Get max retries."""
        return self.source.provider_config.client.max_retries

    @property
    def base_url(self) -> str | None:
        """Get base URL."""
        return self.source.provider_config.base_url

    def to_adapter_config(self, default_page_size: int = 1000) -> DomainAdapterConfig:
        """Convert source config to domain AdapterConfig.

        Creates an immutable domain configuration object from YAML settings.
        This is the single source of truth for adapter parameters.

        Args:
            default_page_size: Default page size if not specified in config.
                Different providers may have different defaults.

        Returns:
            DomainAdapterConfig: Immutable adapter configuration.

        Example:
            >>> config = SourceYamlConfig.model_validate(yaml_data)
            >>> adapter_config = config.to_adapter_config()
            >>> adapter_config.batch_size
            20
        """
        return DomainAdapterConfig(
            batch_size=self.batch_size,
            page_size=(
                self.page_size if self.page_size is not None else default_page_size
            ),
            timeout_sec=self.timeout_sec,
            max_retries=self.max_retries,
        )


__all__ = [
    "CircuitBreakerYamlConfig",
    "ClientYamlConfig",
    "ProviderConfigYaml",
    "RateLimitYamlConfig",
    "SourceSectionConfig",
    "SourceYamlConfig",
]
