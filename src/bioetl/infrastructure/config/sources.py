"""Infrastructure helpers for locating and reading configuration YAML files."""

from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
from typing import Any

import yaml

from bioetl.domain.transform.merge import deep_merge

CONFIGS_ROOT_ENV = "BIOETL_CONFIG_DIR"
DEFAULT_CONFIGS_ROOT = Path("configs")


def get_configs_root(base_dir: str | Path | None = None) -> Path:
    """Return resolved configs root (honours BIOETL_CONFIG_DIR)."""

    if base_dir is not None:
        return Path(base_dir)
    return Path(os.environ.get(CONFIGS_ROOT_ENV, DEFAULT_CONFIGS_ROOT))


def resolve_pipeline_config_path(
    pipeline_id: str, *, base_dir: str | Path | None = None
) -> Path:
    """Return path to pipeline YAML by id '<provider>.<entity>'."""

    try:
        provider, entity = pipeline_id.split(".", maxsplit=1)
    except ValueError as exc:
        raise ValueError("Pipeline id must be in format '<provider>.<entity>'") from exc

    root = get_configs_root(base_dir)
    return root / "pipelines" / provider / f"{entity}.yaml"


def read_yaml(path: Path) -> dict[str, Any]:
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
        merged = deep_merge(merged, profile_data)
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
        merged = deep_merge(merged, base_profile)
    merged = deep_merge(merged, config)
    merged.pop("extends", None)
    return merged


def read_yaml_for_pipeline(
    pipeline_id: str,
    *,
    profile: str | None = None,
    base_dir: str | Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Read pipeline YAML by id with optional profile merge."""

    config_path = resolve_pipeline_config_path(pipeline_id, base_dir=base_dir)
    return read_yaml_from_path(
        config_path,
        profile=profile,
        profiles_root=get_configs_root(base_dir) / "profiles",
    )


def read_yaml_from_path(
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
    raw_config = read_yaml(path)
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

    profile_data = read_yaml(profile_path)
    parent = profile_data.get("extends")
    if parent:
        parent_data = _resolve_profile(parent, profiles_root=profiles_root)
        profile_data = deep_merge(parent_data, profile_data)
    return profile_data


__all__ = [
    "CONFIGS_ROOT_ENV",
    "DEFAULT_CONFIGS_ROOT",
    "get_configs_root",
    "resolve_pipeline_config_path",
    "read_yaml",
    "read_yaml_for_pipeline",
    "read_yaml_from_path",
]
