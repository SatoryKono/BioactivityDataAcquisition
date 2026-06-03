"""Public composite-runtime composition API."""

from __future__ import annotations

from pathlib import Path

from bioetl.composition.bootstrap.runtime.composite import (
    bootstrap_composite_runner,
    load_composite_config,
)
from bioetl.infrastructure.config.config_root import resolve_config_subdir
from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config


_NON_FACTORY_ENTITY_PROVIDERS = frozenset({"composite"})

__all__ = [
    "bootstrap_composite_runner",
    "list_configured_pipeline_names",
    "load_composite_config",
    "load_pipeline_config",
]


def list_configured_pipeline_names(*, configs_root: Path | None = None) -> list[str]:
    """Return configured entity pipeline names without runtime registration."""
    entities_root = resolve_config_subdir("entities", configs_root=configs_root)
    if not entities_root.exists():
        return []

    return sorted(
        f"{path.parent.name}_{path.stem}"
        for path in entities_root.glob("*/*.yaml")
        if path.is_file() and path.parent.name not in _NON_FACTORY_ENTITY_PROVIDERS
    )
