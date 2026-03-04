"""Pipeline Factory - backward-compatibility re-export facade.

All implementation has been extracted to:
- pipeline_assembler.py: GenericPipelineFactory, assemble_runner, create_pipeline_factory
- service_bundle_factory.py: build_pipeline_services, create_pipeline_with_services
"""

from __future__ import annotations

from bioetl.composition.factories.pipeline_assembler import (
    GenericPipelineFactory,
    assemble_runner,
    create_pipeline_factory,
)
from bioetl.composition.factories.service_bundle_factory import (
    build_pipeline_services,
    create_pipeline_with_services,
)

__all__ = [
    "GenericPipelineFactory",
    "assemble_runner",
    "build_pipeline_services",
    "create_pipeline_factory",
    "create_pipeline_with_services",
]
