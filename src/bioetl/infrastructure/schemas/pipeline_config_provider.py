# mypy: disable-error-code="misc"
"""Provider/source schemas extracted from pipeline_config."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from bioetl.infrastructure.schemas.source_config import (
    ClientYamlConfig,
    ProviderConfigYaml,
    RateLimitYamlConfig,
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
    """Entity-level pipeline source request data.

    Provider HTTP transport (``rate_limit``, ``circuit_breaker``,
    ``provider_config``) is owned by ``configs/providers/*.yaml``. Credentials
    resolve through typed Settings / ``api_key_env``, never ``api_key``.
    """

    model_config = ConfigDict(extra="forbid")

    email: str | None = None
    fields: list[dict[str, str]] = Field(default_factory=list)
    api: ApiConfig = Field(default_factory=ApiConfig)
