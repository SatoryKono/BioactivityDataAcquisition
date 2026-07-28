"""Aggregate protocol contracts for pipeline service bundles."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bioetl.application.core.pipeline_aux_service_protocols import (
    PipelineDQServicesProtocol,
    PipelineExecutionServicesProtocol,
    PipelineMetadataServicesProtocol,
    PipelinePostrunServicesProtocol,
)
from bioetl.application.core.pipeline_observability_service_protocols import (
    PipelineLoggingServicesProtocol,
    PipelineObservabilityServicesProtocol,
    PipelineRunnerServicesProtocol,
)
from bioetl.application.core.pipeline_runtime_service_protocols import (
    PipelineDataSourceServicesProtocol,
    PipelineHealthServicesProtocol,
    PipelineManagedRuntimeServicesProtocol,
    PipelineRuntimeControlServicesProtocol,
    PipelineStorageProtocol,
)


@runtime_checkable
class PipelineServicesProtocol(
    PipelineManagedRuntimeServicesProtocol,
    PipelineObservabilityServicesProtocol,
    PipelineMetadataServicesProtocol,
    PipelineDQServicesProtocol,
    Protocol,
):
    """Full aggregate surface retained as a compatibility facade."""

__all__ = [
    "PipelineDQServicesProtocol",
    "PipelineDataSourceServicesProtocol",
    "PipelineExecutionServicesProtocol",
    "PipelineHealthServicesProtocol",
    "PipelineLoggingServicesProtocol",
    "PipelineManagedRuntimeServicesProtocol",
    "PipelineMetadataServicesProtocol",
    "PipelineObservabilityServicesProtocol",
    "PipelinePostrunServicesProtocol",
    "PipelineRunnerServicesProtocol",
    "PipelineRuntimeControlServicesProtocol",
    "PipelineServicesProtocol",
    "PipelineStorageProtocol",
]
