"""Configuration protocols for decoupling infrastructure from application."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from bioetl.domain.providers import BaseProviderConfig as ProviderConfigBase


class PipelineConfigProtocol(Protocol):
    """Protocol exposing the portions of pipeline config used by infrastructure."""

    id: str
    provider: str
    entity: str
    provider_config: ProviderConfigBase
    normalization: Any
    hashing: Any
    pipeline: dict[str, Any]
    fields: list[dict[str, Any]]

    @property
    def entity_name(self) -> str:
        ...


class PipelineConfigLoaderProtocol(Protocol):
    """Protocol for functions capable of loading pipeline configs."""

    def __call__(
        self,
        config_path: str | Path,
        profile: str | None = None,
        profiles_root: Path | None = None,
    ) -> PipelineConfigProtocol:
        ...


__all__ = ["PipelineConfigProtocol", "PipelineConfigLoaderProtocol"]
