# mypy: disable-error-code="misc"
"""Provider/source schemas extracted from pipeline_config."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from bioetl.infrastructure.schemas.pipeline_config_common import (
    CircuitBreakerYamlConfig,
)

__all__ = [
    "ApiConfig",
    "ClientSourceConfig",
    "ProviderSourceConfig",
    "RateLimitSourceConfig",
    "SourceConfig",
]


class ApiConfig(BaseModel):
    """Configuration for API connection details."""

    base_url: str | None = None
    from_db: str | None = Field(
        default=None, description="Source database for ID mapping (e.g., ChEMBL)"
    )
    to_db: str | None = Field(
        default=None, description="Target database for ID mapping (e.g., UniProtKB)"
    )


class RateLimitSourceConfig(BaseModel):
    """Rate limit configuration from source YAML."""

    requests_per_second: float = Field(default=5.0, ge=0.1, le=100.0)
    burst: int = Field(default=10, ge=1, le=200)


class ClientSourceConfig(BaseModel):
    """HTTP client configuration from source YAML."""

    timeout_sec: float = Field(default=30.0, ge=1.0, le=300.0)
    max_retries: int = Field(default=3, ge=0, le=10)


class ProviderSourceConfig(BaseModel):
    """Pipeline-level provider source overrides.

    Pipeline configs may override provider identity and client wiring, but must
    not redefine source pagination defaults here. Pagination is owned by the
    provider source config and pipelines may only influence page size through
    ``page_size_override`` on ``PipelineYamlConfig``.
    """

    model_config = ConfigDict(extra="ignore")

    provider: str | None = None
    base_url: str | None = None
    client: ClientSourceConfig = Field(default_factory=ClientSourceConfig)
    api_version: str | None = None
    default_email: str | None = None


class SourceConfig(BaseModel):
    """Configuration for the data source."""

    model_config = ConfigDict(extra="ignore")

    email: str | None = None
    api_key: str | None = None
    fields: list[dict[str, str]] = Field(default_factory=list)
    api: ApiConfig = Field(default_factory=ApiConfig)
    batch_size: int = Field(default=100, ge=1, le=5000)
    rate_limit: RateLimitSourceConfig = Field(default_factory=RateLimitSourceConfig)
    circuit_breaker: CircuitBreakerYamlConfig = Field(
        default_factory=CircuitBreakerYamlConfig
    )
    provider_config: ProviderSourceConfig = Field(default_factory=ProviderSourceConfig)
