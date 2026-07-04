"""
Path and discovery helpers for canonical composite runtime configs.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from bioetl.infrastructure.config.config_root import resolve_config_subdir

DEFAULT_COMPOSITE_CONFIG_DIR = Path("configs/composites")


def resolve_composite_config_dir(
    *,
    config_dir: Path | None = None,
    configs_root: Path | None = None,
) -> Path:
    """Resolve the canonical composite config directory independent of cwd."""
    return resolve_config_subdir(
        config_dir or DEFAULT_COMPOSITE_CONFIG_DIR,
        configs_root=configs_root,
    )


def resolve_composite_config_path(
    name: str,
    *,
    config_dir: Path | None = None,
    configs_root: Path | None = None,
) -> Path:
    """Resolve composite config path from the canonical composites directory."""
    config_path = (
        resolve_composite_config_dir(
            config_dir=config_dir,
            configs_root=configs_root,
        )
        / f"{name}.yaml"
    )
    if config_path.exists():
        return config_path
    raise FileNotFoundError(f"Composite config not found: {config_path}")


def list_composite_config_names(
    *,
    config_dir: Path | None = None,
    configs_root: Path | None = None,
) -> tuple[str, ...]:
    """Return runtime composite config names, excluding sidecar policy files."""
    composite_dir = resolve_composite_config_dir(
        config_dir=config_dir,
        configs_root=configs_root,
    )
    names: list[str] = []
    for path in sorted(composite_dir.glob("*.yaml")):
        try:
            raw_payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        if isinstance(raw_payload, dict) and isinstance(raw_payload.get("composite"), dict):
            names.append(path.stem)
    return tuple(names)
