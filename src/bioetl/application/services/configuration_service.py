"""Centralized configuration service for application layer.

This module provides a unified service for loading and managing
pipeline configurations, abstracting the details of configuration
resolution and loading.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.domain.ports.config_loader_port import (
        ConfigLoaderPortABC,
        ConfigPathResolverPortABC,
    )
    from bioetl.domain.configs.pipeline import PipelineConfig


@dataclass(frozen=True)
class ConfigurationRequest:
    """Request for loading configuration.

    Encapsulates all parameters needed to load a pipeline configuration.

    Attributes:
        pipeline_id: Pipeline identifier (e.g., "chembl.activity").
        config_path: Explicit path to configuration file.
        profile: Profile name for environment-specific settings.
        cli_overrides: Command-line argument overrides.
        env_overrides: Environment variable overrides.
        base_dir: Base directory for configurations.

    Note:
        Either pipeline_id or config_path must be provided.
    """

    pipeline_id: str | None = None
    config_path: Path | None = None
    profile: str | None = None
    cli_overrides: dict[str, Any] | None = None
    env_overrides: dict[str, Any] | None = None
    base_dir: Path | None = None

    def __post_init__(self) -> None:
        """Validate that either pipeline_id or config_path is provided."""
        if self.pipeline_id is None and self.config_path is None:
            raise ValueError("Either pipeline_id or config_path must be provided")


class ConfigurationService:
    """Centralized service for all configuration operations.

    Provides a unified interface for loading and managing pipeline
    configurations, with support for profiles, overrides, and path
    resolution.

    Example:
        >>> service = ConfigurationService(loader, path_resolver)
        >>> config = service.load(ConfigurationRequest(
        ...     pipeline_id="chembl.activity",
        ...     profile="production",
        ... ))
    """

    def __init__(
        self,
        loader: "ConfigLoaderPortABC",
        path_resolver: "ConfigPathResolverPortABC",
    ) -> None:
        """Initialize service with required dependencies.

        Args:
            loader: Configuration loader port.
            path_resolver: Configuration path resolver port.
        """
        self._loader = loader
        self._path_resolver = path_resolver

    def load(self, request: ConfigurationRequest) -> "PipelineConfig":
        """Load configuration based on request parameters.

        Args:
            request: Configuration request with all parameters.

        Returns:
            Loaded and validated PipelineConfig.

        Raises:
            ValueError: If request is invalid.
            FileNotFoundError: If configuration file not found.
        """
        if request.config_path:
            return self._loader.get_from_path(
                request.config_path,
                profile=request.profile,
                cli_overrides=request.cli_overrides,
            )

        if request.pipeline_id:
            return self._loader.get_by_id(
                request.pipeline_id,
                profile=request.profile,
                cli_overrides=request.cli_overrides,
                env_overrides=request.env_overrides,
                base_dir=request.base_dir,
            )

        raise ValueError("Either pipeline_id or config_path must be provided")

    def load_by_id(
        self,
        pipeline_id: str,
        *,
        profile: str | None = None,
        cli_overrides: dict[str, Any] | None = None,
    ) -> "PipelineConfig":
        """Load configuration by pipeline ID.

        Convenience method for loading by ID without creating a request.

        Args:
            pipeline_id: Pipeline identifier.
            profile: Optional profile name.
            cli_overrides: Optional CLI overrides.

        Returns:
            Loaded PipelineConfig.
        """
        return self.load(
            ConfigurationRequest(
                pipeline_id=pipeline_id,
                profile=profile,
                cli_overrides=cli_overrides,
            )
        )

    def load_from_path(
        self,
        config_path: Path,
        *,
        profile: str | None = None,
    ) -> "PipelineConfig":
        """Load configuration from explicit path.

        Convenience method for loading from path without creating a request.

        Args:
            config_path: Path to configuration file.
            profile: Optional profile name.

        Returns:
            Loaded PipelineConfig.
        """
        return self.load(
            ConfigurationRequest(
                config_path=config_path,
                profile=profile,
            )
        )

    def get_configs_root(self) -> Path:
        """Get root directory for configurations.

        Returns:
            Path to configurations root directory.
        """
        return self._path_resolver.get_configs_root()

    def resolve_pipeline_path(self, pipeline_id: str) -> Path:
        """Resolve configuration path for pipeline ID.

        Args:
            pipeline_id: Pipeline identifier.

        Returns:
            Path to pipeline configuration file.
        """
        return self._path_resolver.resolve_pipeline_path(pipeline_id)

    def list_available_pipelines(self) -> list[str]:
        """List all available pipeline IDs.

        Scans the configuration directory for available pipelines.

        Returns:
            Sorted list of pipeline IDs.
        """
        configs_root = self.get_configs_root()
        pipelines: list[str] = []

        pipelines_dir = configs_root / "pipelines"
        if not pipelines_dir.exists():
            return pipelines

        for provider_dir in pipelines_dir.iterdir():
            if provider_dir.is_dir() and not provider_dir.name.startswith("_"):
                for config_file in provider_dir.glob("*.yaml"):
                    pipeline_id = f"{provider_dir.name}.{config_file.stem}"
                    pipelines.append(pipeline_id)

        return sorted(pipelines)


__all__ = [
    "ConfigurationRequest",
    "ConfigurationService",
]
