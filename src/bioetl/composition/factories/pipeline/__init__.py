# pyright: reportImportCycles=false
"""Public pipeline-factory imports; registry API lives in ``composition.registry_api``."""

from __future__ import annotations

from importlib import import_module

_ASSEMBLER_MODULE = "bioetl.composition.factories.pipeline.assembler"
_BUNDLE_MODULE = "bioetl.composition.factories.services.bundle"


def __getattr__(name: str) -> object:
    """Expose pipeline assembly helpers without importing the factory graph."""
    if name in {
        "GenericPipelineFactory",
        "assemble_runner",
        "create_pipeline_factory",
    }:
        return getattr(import_module(_ASSEMBLER_MODULE), name)
    if name == "build_pipeline_services":
        return getattr(import_module(_BUNDLE_MODULE), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "GenericPipelineFactory",
    "assemble_runner",
    "build_pipeline_services",
    "create_pipeline_factory",
]
