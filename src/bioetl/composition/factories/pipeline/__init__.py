"""Pipeline factory subpackage.

Canonical import paths::

    GenericPipelineFactory : from bioetl.composition.factories.pipeline import GenericPipelineFactory
    PIPELINE_CONFIGS       : from bioetl.composition.factories.pipeline.registry_manifest import PIPELINE_CONFIGS
    register_all_pipelines : from bioetl.composition.factories.pipeline.registry import register_all_pipelines
    PipelineRegistry       : from bioetl.composition import PipelineRegistry

Compatibility path::

    PIPELINE_CONFIGS       : from bioetl.composition.factories.pipeline.configs import PIPELINE_CONFIGS
"""

from __future__ import annotations

from bioetl.composition.factories.pipeline.assembler import (
    GenericPipelineFactory,
    assemble_runner,
    create_pipeline_factory,
)
from bioetl.composition.factories.services.bundle import build_pipeline_services

__all__ = [
    "GenericPipelineFactory",
    "assemble_runner",
    "build_pipeline_services",
    "create_pipeline_factory",
]
