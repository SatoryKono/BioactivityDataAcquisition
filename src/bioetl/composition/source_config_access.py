"""Composition-facing seam for source configuration access."""

from __future__ import annotations

from importlib import import_module


def load_source_config(*args: object, **kwargs: object) -> object:
    """Load source config lazily to keep the public seam import-light."""
    module = import_module("bioetl.infrastructure.config.source_config_loader")
    return module.load_source_config(*args, **kwargs)

__all__ = ["load_source_config"]
