"""Port for configuration loading operations.

This module defines abstract interfaces for configuration loading,
allowing the application layer to work with configurations without
depending on infrastructure details.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from bioetl.domain.configs.pipeline import PipelineConfig


class ConfigLoaderPortABC(ABC):
    """Abstract port for loading pipeline configurations.

    This port abstracts away the infrastructure details of how configurations
    are loaded (YAML files, environment variables, etc.), providing a clean
    interface for the application layer.

    Example:
        >>> class YamlConfigLoader(ConfigLoaderPortABC):
        ...     def get_by_id(self, pipeline_id: str, **kwargs) -> PipelineConfig:
        ...         # Load from YAML file
        ...         ...
    """

    @abstractmethod
    def get_by_id(
        self,
        pipeline_id: str,
        *,
        profile: str | None = None,
        cli_overrides: dict[str, Any] | None = None,
        env_overrides: dict[str, Any] | None = None,
        base_dir: Path | None = None,
    ) -> PipelineConfig:
        """Load pipeline config by ID (e.g., 'chembl.activity').

        Args:
            pipeline_id: Pipeline identifier in 'provider.entity' format.
            profile: Optional profile name for environment-specific settings.
            cli_overrides: Command-line argument overrides.
            env_overrides: Environment variable overrides.
            base_dir: Base directory for configuration files.

        Returns:
            Loaded and validated PipelineConfig.

        Raises:
            FileNotFoundError: If configuration file doesn't exist.
            ValidationError: If configuration is invalid.
        """
        ...

    @abstractmethod
    def get_from_path(
        self,
        config_path: Path,
        *,
        profile: str | None = None,
        cli_overrides: dict[str, Any] | None = None,
        profiles_root: Path | None = None,
    ) -> PipelineConfig:
        """Load pipeline config from explicit file path.

        Args:
            config_path: Path to configuration file.
            profile: Optional profile name for environment-specific settings.
            cli_overrides: Command-line argument overrides.
            profiles_root: Root directory for profile files.

        Returns:
            Loaded and validated PipelineConfig.

        Raises:
            FileNotFoundError: If configuration file doesn't exist.
            ValidationError: If configuration is invalid.
        """
        ...


class ConfigPathResolverPortABC(ABC):
    """Abstract port for resolving configuration paths.

    This port abstracts the logic of finding configuration files
    based on pipeline IDs or other identifiers.
    """

    @abstractmethod
    def get_configs_root(self) -> Path:
        """Return root directory for configurations.

        Returns:
            Path to the configurations root directory.
        """
        ...

    @abstractmethod
    def resolve_pipeline_path(self, pipeline_id: str) -> Path:
        """Resolve path for a pipeline ID.

        Args:
            pipeline_id: Pipeline identifier in 'provider.entity' format.

        Returns:
            Path to the pipeline configuration file.

        Raises:
            FileNotFoundError: If configuration file doesn't exist.
        """
        ...


__all__ = ["ConfigLoaderPortABC", "ConfigPathResolverPortABC"]

