"""Path resolution implementation.

This module provides a concrete PathResolver implementation that handles
path resolution for configuration files, output directories, and input data.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from bioetl.domain.ports.filesystem import PathResolverABC


@dataclass(frozen=True)
class PathResolver(PathResolverABC):
    """Immutable path resolver for configuration and output paths.

    Provides unified path resolution logic, eliminating duplicate code
    across configuration loading and output writing modules.

    Attributes:
        _base_path: The base directory for resolving relative paths.

    Example:
        >>> resolver = PathResolver(Path("configs"))
        >>> resolver.resolve("pipelines/chembl/activity.yaml")
        PosixPath('/absolute/path/configs/pipelines/chembl/activity.yaml')
    """

    _base_path: Path

    @property
    def base_path(self) -> Path:
        """Return the base path used for resolution."""
        return self._base_path

    def resolve(self, path: str | Path) -> Path:
        """Resolve a path relative to the base path.

        If the path is absolute, it is returned as-is (resolved).
        If the path is relative, it is resolved against base_path.

        Args:
            path: Path to resolve (absolute or relative).

        Returns:
            Resolved absolute path.
        """
        p = Path(path).expanduser()
        if p.is_absolute():
            return p.resolve()
        return (self._base_path / p).resolve()

    def resolve_config(self, name: str) -> Path:
        """Resolve a configuration file path.

        Handles two naming conventions:
        1. Direct paths: "pipelines/chembl/activity.yaml"
        2. Pipeline IDs: "chembl.activity" -> "pipelines/chembl/activity.yaml"

        Args:
            name: Configuration name, path fragment, or pipeline ID.

        Returns:
            Resolved absolute path to configuration file.
        """
        # Check if it's a pipeline ID format (provider.entity)
        if "." in name and "/" not in name and not name.endswith((".yaml", ".yml")):
            parts = name.split(".", maxsplit=1)
            if len(parts) == 2:
                provider, entity = parts
                name = f"pipelines/{provider}/{entity}.yaml"

        return self.resolve(name)

    def resolve_output(self, name: str) -> Path:
        """Resolve an output file path.

        Resolves output file paths relative to base path and ensures
        parent directories exist.

        Args:
            name: Output file name or relative path.

        Returns:
            Resolved absolute path to output file with parent dirs created.
        """
        resolved = self.resolve(name)
        return self.ensure_parent_exists(resolved)

    def ensure_parent_exists(self, path: Path) -> Path:
        """Ensure the parent directory of a path exists.

        Creates parent directories if they don't exist (like mkdir -p).
        This is an idempotent operation.

        Args:
            path: Path whose parent directory should be ensured.

        Returns:
            The original path (for method chaining).
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def resolve_existing(self, path: str | Path) -> Path | None:
        """Resolve a path only if it exists.

        Attempts to resolve the path and returns it only if the
        resolved path exists on the filesystem.

        Args:
            path: Path to resolve and check.

        Returns:
            Resolved path if it exists, None otherwise.
        """
        resolved = self.resolve(path)
        return resolved if resolved.exists() else None


# Environment variable for config directory override
CONFIGS_ROOT_ENV = "BIOETL_CONFIG_DIR"
DEFAULT_CONFIGS_ROOT = Path("configs")


def create_config_resolver(base_dir: str | Path | None = None) -> PathResolver:
    """Create a PathResolver for configuration files.

    Respects the BIOETL_CONFIG_DIR environment variable for configuration
    directory override.

    Args:
        base_dir: Override base directory. If None, uses environment
            variable or default "configs" directory.

    Returns:
        PathResolver configured for config file resolution.
    """
    if base_dir is not None:
        return PathResolver(Path(base_dir))
    env_dir = os.environ.get(CONFIGS_ROOT_ENV)
    if env_dir:
        return PathResolver(Path(env_dir))
    return PathResolver(DEFAULT_CONFIGS_ROOT)


def create_output_resolver(output_dir: str | Path) -> PathResolver:
    """Create a PathResolver for output files.

    Args:
        output_dir: Base directory for output files.

    Returns:
        PathResolver configured for output file resolution.
    """
    return PathResolver(Path(output_dir))


__all__ = [
    "PathResolver",
    "CONFIGS_ROOT_ENV",
    "DEFAULT_CONFIGS_ROOT",
    "create_config_resolver",
    "create_output_resolver",
]
