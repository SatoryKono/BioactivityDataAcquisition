"""Filesystem helpers for project-memory package resources."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

MEMORY_ROOT = Path(__file__).resolve().parent
POLICY_DIR = MEMORY_ROOT / "policy"
CATALOG_DIR = MEMORY_ROOT / "catalog"
SCHEMA_DIR = MEMORY_ROOT / "schemas"

REQUIRED_POLICY_FILES = (
    "source_priority.yaml",
    "promotion.yaml",
    "storage.yaml",
    "retention.yaml",
    "confidence.yaml",
    "freshness.yaml",
    "invalidation.yaml",
    "exclusions.yaml",
    "security.yaml",
)

REQUIRED_CATALOG_FILES = (
    "source_registry.yaml",
    "owner_map.yaml",
    "domain_map.yaml",
    "repo_zones.yaml",
    "placement_rules.yaml",
)

REQUIRED_SCHEMA_FILES = (
    "memory_record.schema.json",
    "rag_chunk.schema.json",
    "graph_node.schema.json",
    "graph_edge.schema.json",
    "graph_relation_record.schema.json",
    "timeline_event.schema.json",
    "curated_note.schema.json",
    "episodic_note.schema.json",
)


def _read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_policy_paths() -> list[Path]:
    """Return the required policy files in deterministic order."""
    return [POLICY_DIR / name for name in REQUIRED_POLICY_FILES]


def iter_catalog_paths() -> list[Path]:
    """Return the required catalog files in deterministic order."""
    return [CATALOG_DIR / name for name in REQUIRED_CATALOG_FILES]


def iter_schema_paths() -> list[Path]:
    """Return the required schema files in deterministic order."""
    return [SCHEMA_DIR / name for name in REQUIRED_SCHEMA_FILES]


def load_yaml_resource(path: Path) -> Any:
    """Load a package YAML resource."""
    return _read_yaml(path)


def load_json_resource(path: Path) -> Any:
    """Load a package JSON resource."""
    return _read_json(path)


def discover_repo_root(start: Path | None = None) -> Path | None:
    """Find the nearest repository root containing src/memory from the cwd upward."""
    current = (start or Path.cwd()).absolute()
    for candidate in (current, *current.parents):
        if (candidate / "src" / "memory").exists():
            return candidate
    return None


def discover_memory_root(start: Path | None = None) -> Path:
    """Prefer the current workspace src/memory path when available."""
    repo_root = discover_repo_root(start)
    if repo_root is not None:
        return repo_root / "src" / "memory"
    return MEMORY_ROOT
