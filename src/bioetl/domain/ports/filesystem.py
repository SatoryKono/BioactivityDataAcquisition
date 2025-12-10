"""Ports for filesystem operations (domain layer).

This module defines the interfaces for filesystem-related components
following the hexagonal architecture pattern.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class PathResolverABC(ABC):
    """Abstract base class for path resolution operations.

    Provides a unified interface for resolving various types of paths
    in the application: configuration files, output directories, and
    input data files.

    Implementations should handle:
    - Environment variable resolution (e.g., BIOETL_CONFIG_DIR)
    - Relative path resolution against base directory
    - Directory creation for output paths
    """

    @property
    @abstractmethod
    def base_path(self) -> Path:
        """Return the base path used for resolution.

        Returns:
            Base directory path for resolving relative paths.
        """

    @abstractmethod
    def resolve(self, path: str | Path) -> Path:
        """Resolve a path relative to the base path.

        If the path is absolute, it is returned as-is (resolved).
        If the path is relative, it is resolved against base_path.

        Args:
            path: Path to resolve (absolute or relative).

        Returns:
            Resolved absolute path.
        """

    @abstractmethod
    def resolve_config(self, name: str) -> Path:
        """Resolve a configuration file path.

        Resolves configuration file paths following the convention:
        <base_path>/<name> for direct names, or
        <base_path>/pipelines/<provider>/<entity>.yaml for pipeline IDs.

        Args:
            name: Configuration name or path fragment.

        Returns:
            Resolved absolute path to configuration file.
        """

    @abstractmethod
    def resolve_output(self, name: str) -> Path:
        """Resolve an output file path.

        Resolves output file paths, typically relative to an output
        directory. Ensures parent directories exist.

        Args:
            name: Output file name or relative path.

        Returns:
            Resolved absolute path to output file.
        """

    @abstractmethod
    def ensure_parent_exists(self, path: Path) -> Path:
        """Ensure the parent directory of a path exists.

        Creates parent directories if they don't exist (like mkdir -p).

        Args:
            path: Path whose parent directory should be ensured.

        Returns:
            The original path (for method chaining).
        """

    @abstractmethod
    def resolve_existing(self, path: str | Path) -> Path | None:
        """Resolve a path only if it exists.

        Attempts to resolve the path and returns it only if the
        resolved path exists on the filesystem.

        Args:
            path: Path to resolve and check.

        Returns:
            Resolved path if it exists, None otherwise.
        """


__all__ = [
    "PathResolverABC",
]
