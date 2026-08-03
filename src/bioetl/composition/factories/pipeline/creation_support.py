"""Public cross-owner support exports for pipeline creation wiring.

This module is the canonical non-private seam for first-party packages that
need creation-wiring contracts and the delegated implementation hook without
importing the private ``_creation_wiring`` module directly.
"""

from __future__ import annotations

from bioetl.composition.factories.pipeline._creation_wiring import (
    _BuildPipelineServicesFn,
    _create_pipeline_with_services_impl,
    _PipelineCreationInputs,
    _PipelineCreationRequest,
    _ServiceBundleDeps,
)

__all__ = [
    "_BuildPipelineServicesFn",
    "_PipelineCreationInputs",
    "_PipelineCreationRequest",
    "_ServiceBundleDeps",
    "_create_pipeline_with_services_impl",
]
