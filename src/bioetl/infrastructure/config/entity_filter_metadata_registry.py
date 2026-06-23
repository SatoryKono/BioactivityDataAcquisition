"""Shared filter-metadata registry support for entity configs."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config_merge import config_merge

_REGISTRY_RELATIVE_PATH = Path("quality/entity_filter_metadata_registry.yaml")


def _load_registry(configs_root: Path) -> JsonDict:
    registry_path = configs_root / _REGISTRY_RELATIVE_PATH
    if not registry_path.exists():
        return {}
    payload = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {}


def load_shared_filter_metadata(
    *,
    configs_root: Path,
    config_rel_path: str,
) -> JsonDict:
    """Return shared ``filters.metadata`` for one entity config path."""
    profiles = _load_registry(configs_root).get("profiles")
    if not isinstance(profiles, dict):
        return {}

    for profile in profiles.values():
        if not isinstance(profile, dict):
            continue
        applies_to = profile.get("applies_to")
        if not isinstance(applies_to, list) or config_rel_path not in applies_to:
            continue
        filter_metadata = profile.get("filter_metadata")
        if isinstance(filter_metadata, dict):
            return deepcopy(filter_metadata)
    return {}


def apply_shared_filter_metadata(
    *,
    configs_root: Path,
    config_path: Path,
    payload: JsonDict,
) -> JsonDict:
    """Merge shared filter metadata into one unified entity payload."""
    try:
        config_rel_path = config_path.relative_to(configs_root).as_posix()
    except ValueError:
        config_rel_path = config_path.as_posix()

    shared_metadata = load_shared_filter_metadata(
        configs_root=configs_root,
        config_rel_path=config_rel_path,
    )
    if not shared_metadata:
        return payload

    merged = dict(payload)
    filters = merged.get("filters")
    filters_mapping = dict(filters) if isinstance(filters, dict) else {}
    existing_metadata = filters_mapping.get("metadata")
    merged_metadata = config_merge(
        shared_metadata,
        existing_metadata if isinstance(existing_metadata, dict) else {},
    )
    filters_mapping["metadata"] = merged_metadata
    merged["filters"] = filters_mapping
    return merged


__all__ = [
    "apply_shared_filter_metadata",
    "load_shared_filter_metadata",
]
