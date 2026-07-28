# pyright: reportImportCycles=false
# Import cycle residual tracked in allowlist (PD3).
"""Pipeline factory subpackage.

Canonical import paths::

    GenericPipelineFactory : from bioetl.composition.factories.pipeline import GenericPipelineFactory
    PIPELINE_CONFIGS       : from bioetl.composition.factories.pipeline.registry_manifest import PIPELINE_CONFIGS
    register_all_pipelines : from bioetl.composition.factories.pipeline.registry import register_all_pipelines
    PipelineRegistry       : from bioetl.composition.registry_api import PipelineRegistry
"""

from __future__ import annotations


def __getattr__(name: str) -> object:
    """Expose pipeline assembly helpers lazily to avoid package import cycles."""
    if name in {
        "GenericPipelineFactory",
        "assemble_runner",
        "create_pipeline_factory",
    }:
        from bioetl.composition.factories.pipeline import assembler as _assembler

        return getattr(_assembler, name)
    if name == "build_pipeline_services":
        from bioetl.composition.factories.services.bundle import (
            build_pipeline_services,
        )

        return build_pipeline_services
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "GenericPipelineFactory",
    "assemble_runner",
    "build_pipeline_services",
    "create_pipeline_factory",
]
