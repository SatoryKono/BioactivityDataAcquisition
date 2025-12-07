"""Contracts for loading pipeline configurations without infrastructure coupling."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from bioetl.domain.configs import PipelineConfig


class PipelineConfigLoaderProtocol(Protocol):
    """
    Port for loading pipeline configurations.

    Implementations live in the infrastructure layer and must provide
    deterministic, validated config objects.
    """

    def get_by_id(
        self,
        pipeline_id: str,
        *,
        profile: str | None = None,
        cli_overrides: dict[str, Any] | None = None,
        env_overrides: dict[str, Any] | None = None,
        base_dir: str | Path | None = None,
    ) -> "PipelineConfig":
        """Get config by pipeline identifier."""

    def get_from_path(
        self,
        config_path: str | Path,
        *,
        profile: str | None = None,
        profiles_root: str | Path | None = None,
        cli_overrides: dict[str, Any] | None = None,
        env_overrides: dict[str, Any] | None = None,
    ) -> "PipelineConfig":
        """Get config from explicit filesystem path."""


__all__ = ["PipelineConfigLoaderProtocol"]
