# mypy: disable-error-code="misc"
"""Provider/source schemas extracted from pipeline_config."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from bioetl.infrastructure.schemas.source_config import (
    ClientYamlConfig,
    ProviderConfigYaml,
    RateLimitYamlConfig,
    SourceCircuitBreakerYamlConfig,
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

    model_config = ConfigDict(extra="forbid")

    base_url: str | None = None
    from_db: str | None = Field(
        default=None, description="Source database for ID mapping (e.g., ChEMBL)"
    )
    to_db: str | None = Field(
        default=None, description="Target database for ID mapping (e.g., UniProtKB)"
    )


RateLimitSourceConfig = RateLimitYamlConfig
ClientSourceConfig = ClientYamlConfig
ProviderSourceConfig = ProviderConfigYaml


class SourceConfig(BaseModel):
    """Configuration for the data source."""

    model_config = ConfigDict(extra="forbid")

    email: str | None = None
    api_key: str | None = None
    fields: list[dict[str, str]] = Field(default_factory=list)
    api: ApiConfig = Field(default_factory=ApiConfig)
    batch_size: int = Field(default=100, ge=1, le=5000)
    rate_limit: RateLimitSourceConfig = Field(default_factory=RateLimitSourceConfig)
    circuit_breaker: SourceCircuitBreakerYamlConfig = Field(
        default_factory=SourceCircuitBreakerYamlConfig
    )
    provider_config: ProviderSourceConfig = Field(default_factory=ProviderSourceConfig)
