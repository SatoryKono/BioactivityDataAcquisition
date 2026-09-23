"""Memory-mapping YAML/JSON IO extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from memory.graph.sync_pkg._core_convert import _read_text

__all__ = [
    "DEFAULT_MEMORY_MAPPING_PATH",
    "LEGACY_MEMORY_MAPPING_PATH",
    "_load_memory_mapping",
    "_mapping_dict_or_empty",
    "_mapping_section",
    "_memory_mapping_path",
    "_read_json",
    "_read_yaml",
]

DEFAULT_MEMORY_MAPPING_PATH = "src/memory/graph/mappings.yaml"
LEGACY_MEMORY_MAPPING_PATH = "configs/quality/neo4j_memory_mapping.yaml"


def _read_yaml(path: Path) -> dict[str, object]:
    loaded = yaml.safe_load(_read_text(path))
    if isinstance(loaded, dict):
        return loaded
    return {}


def _read_json(path: Path) -> dict[str, object]:
    loaded = json.loads(_read_text(path))
    if isinstance(loaded, dict):
        return loaded
    return {}


def _load_memory_mapping(root: Path) -> dict[str, object]:
    mapping_path = _memory_mapping_path(root)
    if not mapping_path.is_file():
        return {}
    return _read_yaml(mapping_path)


def _mapping_section(
    memory_mapping: dict[str, object], section: str
) -> dict[str, object]:
    return _mapping_dict_or_empty(memory_mapping.get(section, {}))


def _memory_mapping_path(root: Path) -> Path:
    preferred = root / DEFAULT_MEMORY_MAPPING_PATH
    if preferred.is_file():
        return preferred
    legacy = root / LEGACY_MEMORY_MAPPING_PATH
    if legacy.is_file():
        return legacy
    return preferred


def _mapping_dict_or_empty(payload: object) -> dict[str, object]:
    if isinstance(payload, dict):
        return payload
    return {}
