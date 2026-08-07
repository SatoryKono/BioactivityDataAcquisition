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

# Public non-underscore aliases for first-party importers that must not
# depend on private `_creation_wiring` symbols directly.
BuildPipelineServicesFn = _BuildPipelineServicesFn
PipelineCreationInputs = _PipelineCreationInputs
PipelineCreationRequest = _PipelineCreationRequest
ServiceBundleDeps = _ServiceBundleDeps
create_pipeline_with_services_impl = _create_pipeline_with_services_impl

__all__ = [
    "BuildPipelineServicesFn",
    "PipelineCreationInputs",
    "PipelineCreationRequest",
    "ServiceBundleDeps",
    "_BuildPipelineServicesFn",
    "_PipelineCreationInputs",
    "_PipelineCreationRequest",
    "_ServiceBundleDeps",
    "_create_pipeline_with_services_impl",
    "create_pipeline_with_services_impl",
]
