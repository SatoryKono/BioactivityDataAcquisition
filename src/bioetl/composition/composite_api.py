"""Public composite-runtime composition API."""

from __future__ import annotations

from bioetl.composition.bootstrap.runtime.composite import (
    bootstrap_composite_runner,
    load_composite_config,
)
from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config

__all__ = [
    "bootstrap_composite_runner",
    "load_composite_config",
    "load_pipeline_config",
]
