"""Runner port interfaces for dependency inversion.

Defines protocols for pipeline runner creation and execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from bioetl.domain.ports.audit import AuditPort
from bioetl.domain.ports.config import PipelineYamlConfigPort, SettingsPort
from bioetl.domain.ports.observability import (
    DQMonitorPort,
    LoggerPort,
    MetricsPort,
    TracingPort,
)

if TYPE_CHECKING:
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.context import CachedBronzeContext, PipelineRunContext
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.types import RunID

__all__ = [
    "ExecutionMetricsReadablePort",
    "ExecutionMetricsRunnerPort",
    "ExecutionObservabilityPort",
    "MetricsExtractorPort",
    "PipelineControlPlaneArtifacts",
    "PipelineCreateRunnerRequest",
    "PipelineCreateWithServicesRequest",
    "PipelineFactoryPort",
    "RunnablePort",
    "RunnerFactoryPort",
]


@runtime_checkable
class RunnablePort(Protocol):
    """Protocol for runnable objects (e.g., PipelineRunner).

    This port abstracts the execution interface for pipelines.
    """

    async def run(self) -> None:
        """Execute the pipeline."""
        ...

    @property
    def shutdown_signal(self) -> object | None:
        """Optional shutdown signal for graceful termination.

        Returns:
            Shutdown signal object or None.
        """
        ...

    @property
    def run_id(self) -> str:
        """Stable run identifier for the current execution."""
        ...


@runtime_checkable
class ExecutionMetricsReadablePort(Protocol):
    """Protocol for runners that expose execution counters."""

    @property
    def execution_metrics(self) -> dict[str, int]:
        """Execution counters keyed by canonical metric names.

        Required keys:
        - ``records_fetched``
        - ``records_bronze``
        - ``records_silver``
        - ``records_gold``
        - ``records_quarantined``
        """
        ...


@runtime_checkable
class ExecutionMetricsRunnerPort(
    RunnablePort,
    ExecutionMetricsReadablePort,
    Protocol,
):
    """Protocol for runners that are executable and expose counters."""


@runtime_checkable
class ExecutionObservabilityPort(Protocol):
    """Protocol for execution-time observability collaborators.

    Keeps the runner-factory contract expressed in terms of observability ports
    rather than a concrete composition bundle type.
    """

    @property
    def logger(self) -> LoggerPort: ...

    @property
    def metrics(self) -> MetricsPort: ...

    @property
    def tracer(self) -> TracingPort | None: ...

    @property
    def audit(self) -> AuditPort: ...

    @property
    def dq_monitor(self) -> DQMonitorPort | None: ...


@dataclass(frozen=True, slots=True)
class PipelineControlPlaneArtifacts:
    """Immutable control-plane identities used while wiring pipeline runners."""

    manifest_id: str | None = None
    execution_fingerprint: str | None = None
    config_hash: str | None = None
    resolved_config_hash: str | None = None
    effective_config_hash: str | None = None
    dq_contract_compatibility_hash: str | None = None
    effective_config_artifact_id: str | None = None
    input_snapshot_fingerprint: str | None = None


@runtime_checkable
class RunnerFactoryPort(Protocol):
    """Port for creating pipeline runners.

    This port abstracts runner creation, allowing the application layer
    to orchestrate pipeline runs without depending on composition layer.

    Implements RULES.md §1.1 - Ports & Adapters architecture.
    """

    def create(
        self,
        context: PipelineRunContext,
    ) -> ExecutionMetricsRunnerPort:
        """Create a configured pipeline runner.

        Args:
            context: Pipeline run context containing all execution parameters.

        Returns:
            Runnable object ready for execution and metric extraction.

        Raises:
            ValueError: If pipeline name is unknown or config is invalid.
            FileNotFoundError: If pipeline config file is missing.
        """
        ...

    def list_pipelines(self) -> list[str]:
        """List all available pipeline names.

        Returns:
            Sorted list of registered pipeline names.
        """
        ...

    def contains(self, pipeline_name: str) -> bool:
        """Check if a pipeline is registered.

        Args:
            pipeline_name: Name of the pipeline to check.

        Returns:
            True if pipeline exists, False otherwise.
        """
        ...


@runtime_checkable
class MetricsExtractorPort(Protocol):
    """Protocol for extracting execution metrics from a runner.

    This port allows the service to collect metrics without
    depending on internal runner structure.
    """

    def extract_metrics(self, runner: ExecutionMetricsReadablePort) -> dict[str, int]:
        """Extract execution metrics from a runner.

        Args:
            runner: Runner exposing the execution-metrics contract.

        Returns:
            Dictionary with metric names and values:
            - records_fetched: Total records retrieved
            - records_bronze: Records written to Bronze
            - records_silver: Records written to Silver
            - records_gold: Records written to Gold
            - records_quarantined: Records sent to quarantine
        """
        ...


@dataclass(frozen=True, slots=True)
class PipelineCreateWithServicesRequest:
    """Canonical pipeline-factory request for service-aware pipeline creation."""

    run_id: RunID
    runtime: RuntimeConfig
    started_at: datetime
    settings: SettingsPort
    logger: LoggerPort
    audit: AuditPort | None = None
    manifest_id: str | None = None
    execution_fingerprint: str | None = None
    config_hash: str | None = None
    resolved_config_hash: str | None = None
    effective_config_hash: str | None = None
    dq_contract_compatibility_hash: str | None = None
    effective_config_artifact_id: str | None = None
    config: PipelineYamlConfigPort | None = None
    filter_config: InputFilterConfig | None = None
    tracer: TracingPort | None = None
    dq_monitor: DQMonitorPort | None = None
    metrics: MetricsPort | None = None
    cached_bronze: CachedBronzeContext | None = None


@dataclass(frozen=True, slots=True)
class PipelineCreateRunnerRequest:
    """Canonical runner-factory request bundling runtime and control-plane inputs."""

    run_id: RunID
    runtime: RuntimeConfig
    started_at: datetime
    settings: SettingsPort
    observability: ExecutionObservabilityPort
    control_plane: PipelineControlPlaneArtifacts = PipelineControlPlaneArtifacts()
    filter_config: InputFilterConfig | None = None
    config: PipelineYamlConfigPort | None = None
    cached_bronze: CachedBronzeContext | None = None


@runtime_checkable
class PipelineFactoryPort(Protocol):
    """Protocol for constructing pipelines and execution runners."""

    pipeline_name: str
    silver_schema: object | None
    pandera_silver_schema: object | None

    def create_with_services(
        self,
        request: PipelineCreateWithServicesRequest,
    ) -> object:
        """Create pipeline with services.

        Args:
            request: Canonical creation request with runtime and service seams.

        Returns:
            Opaque assembled pipeline instance ready for runner wiring.
        """
        ...

    def create_runner(
        self,
        request: PipelineCreateRunnerRequest,
    ) -> ExecutionMetricsRunnerPort:
        """Create pipeline runner.

        Args:
            request: Canonical request with runtime, observability, and optional
                control-plane identities for runner construction.

        Returns:
            Runnable execution object exposing the metrics runner contract.
        """
        ...
