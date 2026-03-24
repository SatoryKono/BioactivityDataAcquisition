"""Compatibility shim for pipeline creation wiring symbols.

Canonical owner:
    bioetl.composition.factories.pipeline._creation_wiring

Deprecated path:
    bioetl.composition.factories.pipeline.creation_api
"""

from __future__ import annotations

from warnings import warn

from bioetl.composition.factories.pipeline._creation_wiring import (
    _BuildPipelineServicesFn,
    _create_pipeline_with_services_impl,
    _PipelineCreationInputs,
    _ServiceBundleDeps,
)

warn(
    "bioetl.composition.factories.services.creation_api is deprecated; "
    "use bioetl.composition.factories.pipeline.creation_api instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "_BuildPipelineServicesFn",
    "_PipelineCreationInputs",
    "_ServiceBundleDeps",
    "_create_pipeline_with_services_impl",
]
