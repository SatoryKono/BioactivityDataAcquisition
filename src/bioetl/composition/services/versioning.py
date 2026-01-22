"""Versioning and reproducibility utilities for pipeline metadata.

Provides functions to compute:
- Git commit hash for reproducibility tracking
- Config hash for change detection
- Pipeline version from config or package

These utilities support PipelineMetadata population as per RULES.md §2.3.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from functools import lru_cache
from importlib.metadata import version as pkg_version
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "compute_config_hash",
    "get_git_commit",
    "get_pipeline_version",
]


@lru_cache(maxsize=1)
def get_git_commit() -> str | None:
    """Get the current git commit hash.

    Returns the short (7-character) git commit hash of HEAD.
    Returns None if:
    - Not in a git repository
    - Git is not installed
    - Any other git error occurs

    Results are cached for the process lifetime since the commit
    doesn't change during execution.

    Returns:
        Short git commit hash (e.g., 'abc1234') or None.

    Example:
        >>> commit = get_git_commit()
        >>> print(commit)  # 'abc1234' or None
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None


def _normalize_for_hash(obj: Any) -> Any:
    """Normalize object for deterministic hashing.

    Converts:
    - Lists to sorted lists (for sets represented as lists)
    - Dicts to sorted key-value pairs
    - None to null string
    - Other values as-is

    Args:
        obj: Object to normalize.

    Returns:
        Normalized object suitable for deterministic JSON serialization.
    """
    if obj is None:
        return None
    if isinstance(obj, dict):
        return {k: _normalize_for_hash(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [_normalize_for_hash(item) for item in obj]
    if isinstance(obj, tuple):
        return [_normalize_for_hash(item) for item in obj]
    return obj


def compute_config_hash(config: PipelineYamlConfig | dict[str, Any]) -> str:
    """Compute SHA256 hash of pipeline configuration.

    Creates a deterministic hash of the configuration for change detection.
    The hash is computed from a normalized JSON representation to ensure
    consistency regardless of dict ordering or whitespace.

    Args:
        config: Pipeline configuration (PipelineYamlConfig or dict).

    Returns:
        SHA256 hash string (64 characters).

    Example:
        >>> config = load_pipeline_config("chembl_activity")
        >>> hash_value = compute_config_hash(config)
        >>> print(hash_value)  # '3a7bd3e2...'
    """
    # Convert Pydantic model to dict if needed
    if hasattr(config, "model_dump"):
        config_dict = config.model_dump(mode="json", exclude_none=True)
    elif hasattr(config, "dict"):
        # Legacy Pydantic v1 support
        config_dict = config.dict(exclude_none=True)
    else:
        config_dict = dict(config)

    # Normalize for deterministic serialization
    normalized = _normalize_for_hash(config_dict)

    # Serialize to JSON with sorted keys and no whitespace
    json_str = json.dumps(normalized, sort_keys=True, separators=(",", ":"))

    # Compute SHA256 hash
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()


def get_pipeline_version(
    config: PipelineYamlConfig | dict[str, Any] | None = None,
) -> str:
    """Get pipeline version from config or fallback to package version.

    Priority:
    1. config.version if available
    2. bioetl package version
    3. "unknown" as last resort

    Args:
        config: Optional pipeline configuration.

    Returns:
        Version string (e.g., '1.0.0' or package version).

    Example:
        >>> version = get_pipeline_version(config)
        >>> print(version)  # '1.0.0'
    """
    # Try to get version from config
    if config is not None:
        # Handle Pydantic model
        if hasattr(config, "version") and config.version:
            return config.version
        # Handle dict
        if isinstance(config, dict) and config.get("version"):
            return config["version"]

    # Fallback to bioetl package version
    try:
        return pkg_version("bioetl")
    except Exception:
        return "unknown"


def get_full_git_commit() -> str | None:
    """Get the full git commit hash (40 characters).

    Similar to get_git_commit() but returns the full hash instead of
    the short version. Useful for exact reproducibility tracking.

    Returns:
        Full git commit hash (e.g., 'abc1234...') or None.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None


def is_git_dirty() -> bool:
    """Check if the git working directory has uncommitted changes.

    Returns:
        True if there are uncommitted changes, False otherwise.
        Returns False if not in a git repository or git is unavailable.
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return bool(result.stdout.strip())
        return False
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return False
