"""Bootstrap functions for pipeline runner service.

Provides bootstrap functions for PipelineRunnerService assembly.
This service provides a unified interface for running pipelines
from any orchestration layer (CLI, REST API, etc.).
"""

from __future__ import annotations

from bioetl.application.services.execution.pipeline_run_context_service import (
    PipelineRunContextService,
)
from bioetl.application.services.execution.pipeline_run_execution_service import (
    PipelineRunExecutionService,
)
from bioetl.application.services.execution.pipeline_runner_service import (
    PipelineRunnerService,
)
from bioetl.composition.bootstrap.runtime.observability import (
    bootstrap_observability_bundle,
)
from bioetl.composition.factories.pipeline.runner import (
    create_metrics_extractor,
    create_runner_factory,
)
from bioetl.composition.occurrence_identity import create_runtime_occurrence_run_id
from bioetl.composition.registry_api import PipelineRegistry
from bioetl.composition.runtime_builders.config_access import get_settings
from bioetl.infrastructure.time import SystemClock

__all__ = ["bootstrap_pipeline_runner_service"]


def _pipeline_run_id_factory() -> str:
    """Factory function for pipeline run IDs."""
    return create_runtime_occurrence_run_id("pipeline_run")


def bootstrap_pipeline_runner_service(
    registry: PipelineRegistry | None = None,
) -> PipelineRunnerService:
    """Bootstrap the PipelineRunnerService with all dependencies.

    Creates a fully configured PipelineRunnerService that can be used
    to run pipelines from any interface (CLI, REST API, etc.).

    Args:
        registry: Optional custom registry for test isolation.
            If None, creates a fresh runtime registry through the composition seam.

    Returns:
        PipelineRunnerService ready for use.

    Example:
        >>> service = bootstrap_pipeline_runner_service()
        >>> options = RunOptions(run_type="incremental", limit=100)
        >>> result = await service.run("chembl_activity", options=options)
    """
    settings = get_settings()
    service_run_id = create_runtime_occurrence_run_id("pipeline_runner_service")
    observability = bootstrap_observability_bundle(
        pipeline="pipeline_runner_service",
        run_id=service_run_id,
        settings=settings,
        log_level="INFO",
    )

    # Create factory and extractor
    runner_factory = create_runner_factory(registry=registry)
    metrics_extractor = create_metrics_extractor()

    return PipelineRunnerService(
        runner_factory=runner_factory,
        metrics_extractor=metrics_extractor,
        logger=observability.logger,
        metrics=observability.metrics,
        audit=observability.audit,
        clock=SystemClock(),
        _context_service=PipelineRunContextService(),
        _execution_service=PipelineRunExecutionService(clock=SystemClock()),
        run_id_factory=_pipeline_run_id_factory,
    )
