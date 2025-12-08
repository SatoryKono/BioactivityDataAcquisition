"""Global configuration models for defaults (domain layer)."""

from __future__ import annotations

from typing import Annotated

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, PositiveInt

from bioetl.domain.configs.pipeline import (
    ClientConfig,
    HashingConfig,
    NormalizationConfig,
)


class HashingDefaultsConfig(BaseModel):
    """Default hashing configuration wrapper."""

    hashing: HashingConfig

    model_config = ConfigDict(extra="forbid")


class NormalizationDefaultsConfig(BaseModel):
    """Default normalization configuration wrapper."""

    normalization: NormalizationConfig

    model_config = ConfigDict(extra="forbid")


class ClientDefaultsConfig(ClientConfig):
    """Default HTTP client limits shared across providers."""

    model_config = ConfigDict(extra="forbid")


class HttpDefaultsConfig(BaseModel):
    """Default HTTP constraints shared across clients."""

    max_url_length: PositiveInt

    model_config = ConfigDict(extra="forbid")


class NetworkHttpDefaultsConfig(BaseModel):
    """HTTP defaults section containing canonical defaults."""

    default: HttpDefaultsConfig
    client: ClientDefaultsConfig | None = None

    model_config = ConfigDict(extra="forbid")


class NetworkDefaultsConfig(BaseModel):
    """Top-level network defaults configuration."""

    http: NetworkHttpDefaultsConfig

    model_config = ConfigDict(extra="forbid")


class SourceDefaultsConfig(BaseModel):
    """Generic source defaults entry (per provider)."""

    provider: str
    base_url: AnyHttpUrl | None = None
    batch_size: PositiveInt | None = None
    max_url_length: PositiveInt | None = None

    model_config = ConfigDict(extra="forbid")


class SourcesDefaultsConfig(BaseModel):
    """Container for provider defaults keyed by source name."""

    sources: dict[str, SourceDefaultsConfig] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class DefaultsConfig(BaseModel):
    """Aggregated defaults used across the system."""

    hashing: HashingDefaultsConfig
    normalization: NormalizationDefaultsConfig
    network: NetworkDefaultsConfig | None = None
    sources: Annotated[dict[str, SourceDefaultsConfig], Field(default_factory=dict)]

    model_config = ConfigDict(extra="forbid")

    def get_source_default(
        self,
        provider: str,
    ) -> SourceDefaultsConfig | None:
        """Return provider defaults if present."""

        return self.sources.get(provider)


__all__ = [
    "DefaultsConfig",
    "HashingDefaultsConfig",
    "NormalizationDefaultsConfig",
    "ClientDefaultsConfig",
    "HttpDefaultsConfig",
    "NetworkDefaultsConfig",
    "NetworkHttpDefaultsConfig",
    "SourceDefaultsConfig",
    "SourcesDefaultsConfig",
]
