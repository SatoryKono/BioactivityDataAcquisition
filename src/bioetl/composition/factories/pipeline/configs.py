"""Compatibility shim for the canonical pipeline registry manifest."""

from __future__ import annotations

from bioetl.composition.factories.pipeline.registry_manifest import (
    PIPELINE_CONFIGS,
    PipelineFactoryConfig,
)

__all__ = ["PIPELINE_CONFIGS", "PipelineFactoryConfig"]
