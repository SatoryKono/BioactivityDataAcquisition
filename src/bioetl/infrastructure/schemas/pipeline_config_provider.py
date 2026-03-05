"""Provider/source schemas extracted from pipeline_config."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from bioetl.infrastructure.schemas.pipeline_config_common import CircuitBreakerConfig

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
    """Provider-specific configuration from source YAML."""

    provider: str | None = None
    base_url: str | None = None
    client: ClientSourceConfig = Field(default_factory=ClientSourceConfig)
    max_url_length: int = Field(default=2000, ge=500, le=8000)
    batch_size: int = Field(default=100, ge=1, le=5000)
    page_size: int = Field(default=1000, ge=100, le=10000)
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
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    provider_config: ProviderSourceConfig = Field(default_factory=ProviderSourceConfig)
