"""Configuration path resolution service.

This module provides application-level services for resolving pipeline
configuration paths based on naming conventions. It extracts the business
logic of configuration path resolution from the CLI layer.
"""

from __future__ import annotations

from pathlib import Path


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

    def resolve(
        self, config_path: str | Path | None, pipeline_name: str | None = None
    ) -> Path:
        """Resolve config path, inferring from pipeline name if needed.

        Args:
            config_path: Explicit path (relative or absolute), or None to infer
            pipeline_name: Pipeline name for inference, e.g. "activity_chembl"

        Returns:
            Resolved absolute path to config file

        Raises:
            FileNotFoundError: If config cannot be resolved or inferred
        """
        if config_path is not None:
            return self._resolve_explicit(Path(config_path))
        if pipeline_name is not None:
            inferred = self._infer_from_pipeline_name(pipeline_name)
            if inferred is not None:
                return inferred
        raise FileNotFoundError(
            f"Cannot resolve config: path={config_path}, pipeline={pipeline_name}"
        )

    def _resolve_explicit(self, config_path: Path) -> Path:
        """Resolve explicit config path to absolute."""
        if config_path.is_absolute() and config_path.exists():
            return config_path
        if config_path.exists():
            return config_path.resolve()
        candidate = (self._configs_root / config_path).resolve()
        if candidate.exists():
            return candidate
        raise FileNotFoundError(f"Config file not found: {config_path}")

    def _infer_from_pipeline_name(self, pipeline_name: str) -> Path | None:
        """Infer config path from pipeline naming convention.

        Convention: {entity}_{provider} -> pipelines/{provider}/{entity}.yaml
        """
        parts = pipeline_name.split("_")
        if len(parts) < 2:
            return None
        entity, provider = parts[0], parts[1]
        candidate = self._configs_root / "pipelines" / provider / f"{entity}.yaml"
        if candidate.exists():
            return candidate
        return None

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
]
