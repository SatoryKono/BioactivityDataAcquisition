"""Composition-facing compatibility seam for composite config access."""

from __future__ import annotations

from bioetl.infrastructure.config.composite_config_api import (
    DEFAULT_COMPOSITE_CONFIG_DIR,
    DEFAULT_COMPOSITE_GOLD_SCHEMA_REGISTRY,
    load_composite_config,
    resolve_composite_config_path,
    resolve_composite_gold_schema,
)

__all__ = [
    "DEFAULT_COMPOSITE_CONFIG_DIR",
    "DEFAULT_COMPOSITE_GOLD_SCHEMA_REGISTRY",
    "load_composite_config",
    "resolve_composite_config_path",
    "resolve_composite_gold_schema",
]
