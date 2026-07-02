"""Helpers for discovering executable composite runtime configs in tests."""

from __future__ import annotations

from pathlib import Path

from bioetl.infrastructure.config.composite_config_api import (
    list_composite_config_names,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COMPOSITES_DIR = PROJECT_ROOT / "configs" / "composites"


def runtime_composite_config_paths(
    composites_dir: Path = DEFAULT_COMPOSITES_DIR,
) -> tuple[Path, ...]:
    """Return only executable composite pipeline configs."""
    return tuple(
        composites_dir / f"{name}.yaml"
        for name in list_composite_config_names(config_dir=composites_dir)
    )


def runtime_composite_config_names(
    composites_dir: Path = DEFAULT_COMPOSITES_DIR,
) -> tuple[str, ...]:
    """Return executable composite pipeline config stems."""
    return list_composite_config_names(config_dir=composites_dir)
