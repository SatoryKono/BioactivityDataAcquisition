"""Composition-facing seam for source configuration access."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from bioetl.infrastructure.schemas.source_config import SourceYamlConfig


def load_source_config(*args: object, **kwargs: object) -> "SourceYamlConfig":
    """Load source config lazily to keep the public seam import-light."""
    module = import_module("bioetl.infrastructure.config.source_config_loader")
    return cast("SourceYamlConfig", module.load_source_config(*args, **kwargs))


__all__ = ["load_source_config"]
