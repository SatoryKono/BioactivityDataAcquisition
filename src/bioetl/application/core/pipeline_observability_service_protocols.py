"""Observability-oriented service protocols for application-core collaborators."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bioetl.application.core.pipeline_runtime_service_protocols import (
    PipelineManagedRuntimeServicesProtocol,
)
from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort


@runtime_checkable
class PipelineLoggingServicesProtocol(Protocol):
    """Services surface that only needs the structured logger seam."""

    logger: LoggerPort


@runtime_checkable
class PipelineObservabilityServicesProtocol(PipelineLoggingServicesProtocol, Protocol):
    """Observability ports shared across runner, batch, and postrun paths."""

    metrics: MetricsPort
    tracing: TracingPort


@runtime_checkable
class PipelineRunnerServicesProtocol(
    PipelineManagedRuntimeServicesProtocol,
    PipelineObservabilityServicesProtocol,
    Protocol,
):
    """Narrow service surface required by the runner lifecycle path."""


__all__ = [
    "PipelineLoggingServicesProtocol",
    "PipelineObservabilityServicesProtocol",
    "PipelineRunnerServicesProtocol",
]
