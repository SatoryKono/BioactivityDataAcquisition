"""Configuration path resolution service.

This module provides application-level services for resolving pipeline
configuration paths based on naming conventions. It extracts the business
logic of configuration path resolution from the CLI layer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bioetl.domain.configs import PipelineConfig
from bioetl.domain.configs.contracts import PipelineConfigLoaderProtocol


class ConfigPathResolver:
    """Resolves config paths based on pipeline naming conventions.

    Pipeline names follow the pattern: <entity>_<provider> (e.g., compound_chembl).
    This resolver infers the config file path from this convention and handles
    fallback resolution logic.
    """

    def __init__(self, configs_root: Path) -> None:
        """Initialize resolver with configs root directory.

        Args:
            configs_root: Base directory for configuration files.
        """
        self._configs_root = configs_root

    @property
    def configs_root(self) -> Path:
        """Return the configured configs root directory."""
        return self._configs_root

    def infer_config_path(self, pipeline_name: str) -> Path | None:
        """Infer config path from pipeline name (entity_provider pattern).

        Args:
            pipeline_name: Pipeline identifier like 'compound_chembl'.

        Returns:
            Path to config file relative to configs_root, or None if pattern
            doesn't match the expected convention.

        Example:
            >>> resolver = ConfigPathResolver(Path("configs"))
            >>> resolver.infer_config_path("compound_chembl")
            Path('pipelines/chembl/compound.yaml')
        """
        parts = pipeline_name.split("_")
        if len(parts) >= 2:
            entity, provider = parts[0], parts[1]
            return Path("pipelines") / provider / f"{entity}.yaml"
        return None

    def resolve_config_path(
        self,
        pipeline_name: str,
        explicit_path: Path | str | None = None,
    ) -> Path:
        """Resolve final config path with fallbacks.

        Resolution order:
        1. If explicit_path is provided and exists, use it directly
        2. If explicit_path is relative, try resolving against configs_root
        3. If no explicit path, infer from pipeline_name convention

        Args:
            pipeline_name: Pipeline identifier for inference fallback.
            explicit_path: Explicit config path if provided by user.

        Returns:
            Resolved absolute path to config file.

        Raises:
            FileNotFoundError: If config file cannot be found.
            ValueError: If pipeline name doesn't match expected pattern and
                no explicit path provided.
        """
        if explicit_path is not None:
            path = Path(explicit_path)
            if path.exists():
                return path.resolve()
            # Try resolving relative to configs_root
            candidate = (self._configs_root / path).resolve()
            if candidate.exists():
                return candidate
            raise FileNotFoundError(f"Config file not found: {explicit_path}")

        # Infer from pipeline name
        inferred = self.infer_config_path(pipeline_name)
        if inferred is None:
            raise ValueError(
                f"Cannot infer config path from pipeline name '{pipeline_name}'. "
                "Expected format: '<entity>_<provider>'. "
                "Use explicit --config option."
            )

        full_path = (self._configs_root / inferred).resolve()
        if full_path.exists():
            return full_path

        raise FileNotFoundError(
            f"Config file not found: {full_path} "
            f"(inferred from pipeline '{pipeline_name}')"
        )


def build_pipeline_config(
    config_path: Path,
    *,
    configs_root: Path | None = None,
    loader: PipelineConfigLoaderProtocol,
    profile: str | None = None,
    cli_overrides: dict[str, Any] | None = None,
    env_overrides: dict[str, Any] | None = None,
) -> PipelineConfig:
    """Load and validate pipeline config from path.

    This function wraps the infrastructure loader with application-level
    defaults for configs_root detection.

    Args:
        config_path: Path to the pipeline config YAML file.
        configs_root: Root directory for configs. If None, inferred from
            config_path parent structure.
        loader: Infrastructure config loader protocol.
        profile: Optional profile name to merge with base config.
        cli_overrides: CLI-provided overrides (highest priority).
        env_overrides: Environment-provided overrides.

    Returns:
        Fully validated PipelineConfig instance.
    """
    effective_configs_root = configs_root
    if effective_configs_root is None:
        effective_configs_root = _infer_configs_root(config_path)

    profiles_root = effective_configs_root / "profiles" if effective_configs_root else None

    return loader.get_from_path(
        config_path,
        profile=profile,
        profiles_root=profiles_root,
        cli_overrides=cli_overrides,
        env_overrides=env_overrides,
    )


def _infer_configs_root(config_path: Path) -> Path:
    """Infer configs root from config file path structure.

    Looks for standard structure: configs/pipelines/<provider>/<entity>.yaml
    and returns the 'configs' directory.

    Args:
        config_path: Path to a pipeline config file.

    Returns:
        Inferred configs root directory, or Path("configs") as fallback.
    """
    # Standard structure: configs/pipelines/<provider>/<entity>.yaml
    # So config_path.parent.parent.parent should be configs root
    # Check if we match the expected pattern
    if config_path.parent.parent.name == "pipelines":
        return config_path.parent.parent.parent
    return Path("configs")


__all__ = [
    "ConfigPathResolver",
    "build_pipeline_config",
]
