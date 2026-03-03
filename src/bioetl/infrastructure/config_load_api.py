"""Leaf load API for pipeline/source configuration.

This module provides a cycle-safe import surface for configuration loaders.
Use this module from ``infrastructure.config`` internals and re-export from
``infrastructure.config.__init__`` for public consumers.
"""

from bioetl.infrastructure.config_loader import load_pipeline_config, load_source_config

__all__ = [
    "load_pipeline_config",
    "load_source_config",
]
