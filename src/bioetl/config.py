"""Public facade for loading validated configuration defaults."""

from __future__ import annotations

from pathlib import Path

from bioetl.domain.configs import DefaultsConfig


def load_defaults(*, base_dir: str | Path | None = None) -> DefaultsConfig:
    """Load system-wide default configurations with validation."""

    from bioetl.infrastructure.config.defaults_loader import load_defaults_config

    return load_defaults_config(base_dir=base_dir)


__all__ = ["load_defaults"]
