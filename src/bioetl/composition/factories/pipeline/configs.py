"""Compatibility shim for the canonical pipeline registry manifest."""

from __future__ import annotations

from warnings import warn

from bioetl.composition.factories.pipeline.registry_manifest import (
    PIPELINE_CONFIGS,
    PipelineFactoryConfig,
)

warn(
    "bioetl.composition.factories.pipeline.configs is deprecated; "
    "use bioetl.composition.factories.pipeline.registry_manifest instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["PIPELINE_CONFIGS", "PipelineFactoryConfig"]
