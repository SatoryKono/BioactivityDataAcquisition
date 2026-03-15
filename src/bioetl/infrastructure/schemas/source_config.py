"""Schema validation for source configuration.

Implements strict validation for source YAML configurations (configs/providers/*.yaml).
These configs define provider-specific settings like rate limits, circuit breaker,
pagination, and batch sizes that were previously hardcoded.

This module uses base classes from `base_schemas` to eliminate duplication
with `pipeline_config.py`.

Pagination parameters are the single source of truth in source configs.
Pipeline configs may only override ``page_size`` via ``page_size_override``.
See ADR-031 for loading strategy formalization.

Usage:
    >>> from bioetl.infrastructure.schemas.source_config import SourceYamlConfig
    >>> config = SourceYamlConfig.model_validate(yaml_data)
    >>> rate_limit = config.source.rate_limit.requests_per_second
    >>> config.pagination.page_size
    1000
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from bioetl.domain.constants import DEFAULT_BATCH_SIZE
from bioetl.domain.resilience import AdapterConfig as DomainAdapterConfig
from bioetl.domain.resilience import CircuitBreakerConfig as DomainCircuitBreakerConfig
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.schemas.base_schemas import (
    BaseCircuitBreakerConfig,
    BaseRateLimitConfig,
    HttpClientConfig,
)
from bioetl.infrastructure.schemas.source_config_pagination_helpers import (
    build_pagination_from_legacy as _build_pagination_from_legacy,
)
from bioetl.infrastructure.schemas.source_config_pagination_helpers import (
    collect_legacy_pagination_values as _collect_legacy_pagination_values,
)
from bioetl.infrastructure.schemas.source_config_pagination_helpers import (
    merge_legacy_into_pagination as _merge_legacy_into_pagination,
)

RateLimitYamlConfig = BaseRateLimitConfig
RateLimitYamlConfig.__doc__ = """Rate limit configuration from YAML."""


class SourceCircuitBreakerYamlConfig(BaseCircuitBreakerConfig):
    """Circuit breaker configuration from YAML.

    Inherits from BaseCircuitBreakerConfig for consistency with other schemas.

    Attributes:
        failure_threshold: Number of consecutive failures before opening circuit.
        recovery_timeout: Time in seconds before attempting recovery.
    """

    def to_domain(self) -> DomainCircuitBreakerConfig:
        """Convert to domain CircuitBreakerConfig dataclass.

        Returns:
            DomainCircuitBreakerConfig: Immutable domain configuration.
        """
        return super().to_domain()


ClientYamlConfig = HttpClientConfig
ClientYamlConfig.__doc__ = """HTTP client configuration from YAML."""


class PaginationConfig(BaseModel):
    """API pagination configuration.

    Single source of truth for all API pagination parameters.
    Defined per-provider in configs/providers/*.yaml.

    Pipelines may only override ``page_size`` via ``page_size_override``
    but cannot redefine the pagination strategy.

    Attributes:
        page_size: Number of records per paginated API page.
        id_batch_size: Number of IDs per filtered query batch.
        strategy: Pagination strategy (offset or cursor).
        max_url_length: Maximum URL length for GET requests.
    """

    model_config = ConfigDict(extra="ignore")

    page_size: int | None = Field(default=None, ge=1, le=10000)
    id_batch_size: int | None = Field(default=None, ge=1, le=5000)
    strategy: Literal["offset", "cursor"] = "offset"
    max_url_length: int | None = Field(default=None, ge=100, le=10000)


class FallbackPolicyYamlConfig(BaseModel):
    """Provider fallback orchestration policy from YAML."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = Field(default=False)
    supported_filter_field: str | None = None
    unsupported_filter_event: str = "unsupported_filter_field_for_fallback"
    unsupported_filter_message: str = (
        "Fallback only supports '{expected}' filtering, skipping"
    )
    skip_on_unsupported_filter_field: bool = True
    primary_lookup_method: str | None = None
    trim_primary_ids_to_limit: bool = False
    fallback_operation: str = "fetch_filtered_with_fallback"


class ProviderConfigYaml(BaseModel):
    """Provider-specific configuration from YAML.

    Attributes:
        provider: Provider name (chembl, pubchem, uniprot, pubmed).
        base_url: Base URL for the API.
        client: HTTP client settings.
        pagination: API pagination settings (single source of truth).
        batch_size: Deprecated — use pagination.id_batch_size.
        page_size: Deprecated — use pagination.page_size.
        max_url_length: Deprecated — use pagination.max_url_length.
        default_email: Default email for NCBI APIs (PubMed specific).
    """

    model_config = ConfigDict(extra="ignore")

    provider: str = ""
    base_url: str | None = None
    client: ClientYamlConfig = Field(default_factory=ClientYamlConfig)
    pagination: PaginationConfig = Field(default_factory=PaginationConfig)
    # Legacy fields — kept for backward compatibility.
    # When set, they are promoted into ``pagination`` by the model_validator.
    batch_size: int | None = Field(default=None, ge=1, le=10000)
    page_size: int | None = Field(default=None, ge=1, le=10000)
    max_url_length: int | None = Field(default=None, ge=100, le=10000)
    api_version: str | None = None
    default_email: str | None = None
    fallback: FallbackPolicyYamlConfig | None = None

    @model_validator(mode="before")
    @classmethod
    def _promote_legacy_pagination(
        cls,
        data: JsonDict,  # Any: YAML config has heterogeneous values
    ) -> JsonDict:  # Any: YAML config has heterogeneous values
        """Promote legacy batch_size/page_size/max_url_length into pagination.

        When the ``pagination`` section is absent but legacy fields are set,
        this validator builds the ``pagination`` dict from them.
        Explicit ``pagination`` values always take precedence.

        Returns:
            Input data dict with pagination section populated from legacy fields.
        """
        if not isinstance(data, dict):
            return data

        pagination = data.get("pagination")
        if isinstance(pagination, dict):
            _merge_legacy_into_pagination(
                pagination, _collect_legacy_pagination_values(data)
            )
            return data

        built_pagination = _build_pagination_from_legacy(data)
        if built_pagination:
            data["pagination"] = built_pagination

        return data


class SourceSectionConfig(BaseModel):
    """Source section configuration from YAML.

    This represents the 'source' section in configs/providers/*.yaml files.

    Attributes:
        batch_size: Batch size for data loading.
        provider_config: Provider-specific settings.
        circuit_breaker: Circuit breaker configuration.
        rate_limit: Rate limiting configuration.
    """

    model_config = ConfigDict(extra="ignore")

    batch_size: int = Field(default=DEFAULT_BATCH_SIZE, ge=1, le=10000)
    provider_config: ProviderConfigYaml = Field(
        default_factory=lambda: ProviderConfigYaml()
    )
    circuit_breaker: SourceCircuitBreakerYamlConfig = Field(
        default_factory=lambda: SourceCircuitBreakerYamlConfig()
    )
    rate_limit: RateLimitYamlConfig = Field(
        default_factory=lambda: RateLimitYamlConfig()
    )


class SourceYamlConfig(BaseModel):
    """Root schema for source configuration files.

    Validates configs/providers/*.yaml files.

    Example YAML:
        source:
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
    def circuit_breaker(self) -> SourceCircuitBreakerYamlConfig:
        """Get circuit breaker config."""
        return self.source.circuit_breaker

    @property
    def pagination(self) -> PaginationConfig:
        """Get pagination config (single source of truth for API pagination)."""
        return self.source.provider_config.pagination

    @property
    def batch_size(self) -> int:
        """Get ID batch size for filtered queries.

        Resolution order:
        1. pagination.id_batch_size (canonical, if explicitly set)
        2. provider_config.batch_size (legacy)
        3. source.batch_size (fallback)
        """
        pag = self.source.provider_config.pagination
        if pag.id_batch_size is not None:
            return pag.id_batch_size
        if self.source.provider_config.batch_size is not None:
            return self.source.provider_config.batch_size
        return self.source.batch_size

    @property
    def page_size(self) -> int | None:
        """Get page size for paginated APIs.

        Resolution order:
        1. pagination.page_size (canonical)
        2. provider_config.page_size (legacy)
        """
        pag = self.source.provider_config.pagination
        if pag.page_size is not None:
            return pag.page_size
        return self.source.provider_config.page_size

    @property
    def max_url_length(self) -> int | None:
        """Get max URL length for APIs.

        Resolution order:
        1. pagination.max_url_length (canonical)
        2. provider_config.max_url_length (legacy)
        """
        pag = self.source.provider_config.pagination
        if pag.max_url_length is not None:
            return pag.max_url_length
        return self.source.provider_config.max_url_length

    @property
    def timeout_sec(self) -> float:
        """Get timeout in seconds."""
        return self.source.provider_config.client.timeout_sec

    @property
    def max_retries(self) -> int:
        """Get max retries."""
        return self.source.provider_config.client.max_retries

    @property
    def retry_base_delay(self) -> float:
        """Get retry base delay in seconds."""
        return self.source.provider_config.client.retry_base_delay

    @property
    def retry_max_delay(self) -> float:
        """Get retry max delay in seconds."""
        return self.source.provider_config.client.retry_max_delay

    @property
    def max_connections(self) -> int:
        """Get max concurrent connections for httpx."""
        return self.source.provider_config.client.max_connections

    @property
    def max_keepalive_connections(self) -> int:
        """Get max keep-alive connections for httpx."""
        return self.source.provider_config.client.max_keepalive_connections

    @property
    def base_url(self) -> str | None:
        """Get base URL."""
        return self.source.provider_config.base_url

    @property
    def fallback(self) -> FallbackPolicyYamlConfig | None:
        """Get fallback execution policy from provider config."""
        return self.source.provider_config.fallback

    def to_adapter_config(
        self,
        default_page_size: int = 1000,
        page_size_override: int | None = None,
    ) -> DomainAdapterConfig:
        """Convert source config to domain AdapterConfig.

        Creates an immutable domain configuration object from YAML settings.
        Pagination parameters are read from the canonical ``pagination`` section.

        Args:
            default_page_size: Default page size if not specified in config.
                Different providers may have different defaults.
            page_size_override: Optional pipeline-level page_size override.
                When set, takes precedence over source pagination config.

        Returns:
            DomainAdapterConfig: Immutable adapter configuration.

        Example:
            >>> config = SourceYamlConfig.model_validate(yaml_data)
            >>> adapter_config = config.to_adapter_config()
            >>> adapter_config.batch_size
            20
        """
        effective_page_size = (
            page_size_override
            if page_size_override is not None
            else (self.page_size if self.page_size is not None else default_page_size)
        )
        return DomainAdapterConfig(
            batch_size=self.batch_size,
            page_size=effective_page_size,
            timeout_sec=self.timeout_sec,
            max_retries=self.max_retries,
        )


__all__ = [
    "ClientYamlConfig",
    "FallbackPolicyYamlConfig",
    "PaginationConfig",
    "ProviderConfigYaml",
    "RateLimitYamlConfig",
    "SourceCircuitBreakerYamlConfig",
    "SourceSectionConfig",
    "SourceYamlConfig",
]
