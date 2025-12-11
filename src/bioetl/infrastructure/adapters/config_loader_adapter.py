"""Infrastructure adapter for config loading port.

This module provides concrete implementations of configuration loading
ports using the infrastructure layer's YAML-based configuration system.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from bioetl.domain.configs.pipeline import PipelineConfig
from bioetl.domain.ports.config_loader_port import (
    ConfigLoaderPortABC,
    ConfigPathResolverPortABC,
)

if TYPE_CHECKING:
    from bioetl.domain.ports.schema import SchemaContractProviderABC


class ConfigLoaderAdapter(ConfigLoaderPortABC):
    """Adapter implementing config loader port.

    This adapter wraps the infrastructure config loading functions,
    providing a clean interface that conforms to the application port.
    """

    def __init__(
        self,
        schema_contract_provider: "SchemaContractProviderABC | None" = None,
    ) -> None:
        """Initialize adapter with optional schema contract provider.

        Args:
            schema_contract_provider: Provider for schema contracts.
                If None, uses default bootstrapped provider.
        """
        self._provider = schema_contract_provider

    def get_by_id(
        self,
        pipeline_id: str,
        *,
        profile: str | None = None,
        cli_overrides: dict[str, Any] | None = None,
        env_overrides: dict[str, Any] | None = None,
        base_dir: Path | None = None,
    ) -> PipelineConfig:
        """Load pipeline config by ID (e.g., 'chembl.activity')."""
        from bioetl.infrastructure.config.loader import get_pipeline_config

        return get_pipeline_config(
            pipeline_id,
            schema_contract_provider=self._provider,
            profile=profile,
            cli_overrides=cli_overrides or {},
            env_overrides=env_overrides or {},
            base_dir=base_dir,
        )

    def get_from_path(
        self,
        config_path: Path,
        *,
        profile: str | None = None,
        cli_overrides: dict[str, Any] | None = None,
        profiles_root: Path | None = None,
    ) -> PipelineConfig:
        """Load pipeline config from explicit file path."""
        from bioetl.infrastructure.config.loader import get_pipeline_config_from_path

        return get_pipeline_config_from_path(
            config_path,
            schema_contract_provider=self._provider,
            profile=profile,
            cli_overrides=cli_overrides or {},
            profiles_root=profiles_root,
        )


class ConfigPathResolverAdapter(ConfigPathResolverPortABC):
    """Adapter implementing config path resolver port.

    This adapter wraps the infrastructure config path resolution functions.
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        """Initialize adapter with optional base directory.

        Args:
            base_dir: Base directory for configurations.
                If None, uses default from environment.
        """
        self._base_dir = base_dir

    def get_configs_root(self) -> Path:
        """Return root directory for configurations."""
        from bioetl.infrastructure.config.sources import get_configs_root

        return get_configs_root(self._base_dir)

    def resolve_pipeline_path(self, pipeline_id: str) -> Path:
        """Resolve path for a pipeline ID."""
        from bioetl.infrastructure.config.sources import resolve_pipeline_config_path

        return resolve_pipeline_config_path(pipeline_id, self._base_dir)


__all__ = ["ConfigLoaderAdapter", "ConfigPathResolverAdapter"]
