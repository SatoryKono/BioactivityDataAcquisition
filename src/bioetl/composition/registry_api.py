"""Public registry-oriented composition API."""

from __future__ import annotations

from bioetl.composition import (
    PipelineDefinition,
    PipelineRegistry,
    create_registry,
    get_default_registry,
)
from bioetl.composition.factories.pipeline.registry import register_all_pipelines

__all__ = [
    "PipelineDefinition",
    "PipelineRegistry",
    "create_registry",
    "get_default_registry",
    "register_all_pipelines",
]
