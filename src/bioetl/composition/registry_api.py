"""Public registry-oriented composition API."""

from __future__ import annotations

from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.registry import (
    PipelineDefinition,
    PipelineRegistry,
    create_registry,
)
from bioetl.composition.registry_default import get_default_registry

__all__ = [
    "PipelineDefinition",
    "PipelineRegistry",
    "create_registry",
    "get_default_registry",
    "register_all_pipelines",
]
