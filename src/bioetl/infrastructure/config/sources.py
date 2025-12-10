"""Infrastructure helpers for locating and reading configuration YAML files."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from bioetl.domain.transform.merge import apply_deep_merge
from bioetl.infrastructure.files.path_resolver import (
    CONFIGS_ROOT_ENV,
    DEFAULT_CONFIGS_ROOT,
    PathResolver,
    create_config_resolver,
)

# Re-export constants for backward compatibility
__all_constants__ = ["CONFIGS_ROOT_ENV", "DEFAULT_CONFIGS_ROOT"]


def get_configs_root(base_dir: str | Path | None = None) -> Path:
    """Return resolved configs root (honours BIOETL_CONFIG_DIR).

    Args:
        base_dir: Override base directory. If None, uses BIOETL_CONFIG_DIR
            environment variable or default "configs" directory.

    Returns:
        Resolved configuration root directory path.
    """
    resolver = create_config_resolver(base_dir)
    return resolver.base_path


def resolve_pipeline_config_path(
    pipeline_id: str, *, base_dir: str | Path | None = None
) -> Path:
    """Return path to pipeline YAML by id '<provider>.<entity>'.

    Args:
        pipeline_id: Pipeline identifier in format 'provider.entity'.
        base_dir: Override base directory for configuration search.

    Returns:
        Resolved path to pipeline configuration file.

    Raises:
        ValueError: If pipeline_id is not in expected format.
    """
    # Validate format before delegating to resolver
    if "." not in pipeline_id:
        raise ValueError("Pipeline id must be in format '<provider>.<entity>'")

    resolver = create_config_resolver(base_dir)
    return resolver.resolve_config(pipeline_id)


def get_yaml(path: Path) -> dict[str, Any]:
    """Read YAML file ensuring mapping root."""

    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: YAML root must be a mapping")
    return data


def _merge_with_profile(
    config: dict[str, Any],
    *,
    profile: str | None,
    profiles_root: Path,
) -> dict[str, Any]:
    merged = dict(config)
    if profile and profile != "default":
        profile_data = _resolve_profile(profile, profiles_root=profiles_root)
        merged = apply_deep_merge(merged, profile_data)
    return merged


def _apply_extends(
    config: dict[str, Any],
    *,
    profiles_root: Path,
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    extends_profile = config.get("extends")
    if extends_profile:
        base_profile = _resolve_profile(extends_profile, profiles_root=profiles_root)
        merged = apply_deep_merge(merged, base_profile)
    merged = apply_deep_merge(merged, config)
    merged.pop("extends", None)
    return merged


def get_yaml_for_pipeline(
    pipeline_id: str,
    *,
    profile: str | None = None,
    base_dir: str | Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Read pipeline YAML by id with optional profile merge."""

    config_path = resolve_pipeline_config_path(pipeline_id, base_dir=base_dir)
    return get_yaml_from_path(
        config_path,
        profile=profile,
        profiles_root=get_configs_root(base_dir) / "profiles",
    )


def get_yaml_from_path(
    config_path: str | Path,
    *,
    profile: str | None = None,
    profiles_root: Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Read pipeline YAML from explicit path with optional profile merge."""

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    effective_profiles_root = profiles_root or path.parent.parent / "profiles"
    raw_config = get_yaml(path)
    merged = _apply_extends(raw_config, profiles_root=effective_profiles_root)
    merged = _merge_with_profile(
        merged,
        profile=profile,
        profiles_root=effective_profiles_root,
    )
    return path, merged


@lru_cache(maxsize=None)
def _resolve_profile(
    profile_name: str,
    *,
    profiles_root: Path,
) -> dict[str, Any]:
    profile_path = profiles_root / f"{profile_name}.yaml"
    if not profile_path.exists():
        raise FileNotFoundError(f"Profile file not found: {profile_path}")

    profile_data = get_yaml(profile_path)
    parent = profile_data.get("extends")
    if parent:
        parent_data = _resolve_profile(parent, profiles_root=profiles_root)
        profile_data = apply_deep_merge(parent_data, profile_data)
    profile_data.pop("extends", None)
    return profile_data


__all__ = [
    "CONFIGS_ROOT_ENV",
    "DEFAULT_CONFIGS_ROOT",
    "get_configs_root",
    "resolve_pipeline_config_path",
    "get_yaml",
    "get_yaml_for_pipeline",
    "get_yaml_from_path",
]
