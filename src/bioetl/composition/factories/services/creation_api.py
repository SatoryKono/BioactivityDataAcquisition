"""Compatibility shim for pipeline creation wiring symbols.

Canonical owner:
    bioetl.composition.factories.pipeline._creation_wiring
"""

from __future__ import annotations

from bioetl.composition.factories.pipeline._creation_wiring import (
    _BuildPipelineServicesFn,
    _create_pipeline_with_services_impl,
    _PipelineCreationInputs,
    _ServiceBundleDeps,
)

__all__ = [
    "_BuildPipelineServicesFn",
    "_PipelineCreationInputs",
    "_ServiceBundleDeps",
    "_create_pipeline_with_services_impl",
]
