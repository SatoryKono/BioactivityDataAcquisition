"""Bootstrap functions for pipeline runner service.

Provides bootstrap functions for PipelineRunnerService assembly.
"""

from __future__ import annotations

from bioetl.application.services import PipelineRunnerService
from bioetl.composition._bootstrap.observability import bootstrap_logger
from bioetl.composition.factories.runner_factory import (
    create_metrics_extractor,
    create_runner_factory,
)
from bioetl.composition.registry import PipelineRegistry


def bootstrap_pipeline_runner_service(
    registry: PipelineRegistry | None = None,
) -> PipelineRunnerService:
    """Bootstrap the PipelineRunnerService with all dependencies.

    Creates a fully configured PipelineRunnerService that can be used
    to run pipelines from any interface (CLI, REST API, etc.).

    Args:
        registry: Optional custom registry for test isolation.
            If None, uses the default global registry.

    Returns:
        PipelineRunnerService ready for use.

    Example:
        >>> service = bootstrap_pipeline_runner_service()
        >>> options = RunOptions(run_type="incremental", limit=100)
        >>> result = await service.run("chembl_activity", options=options)
    """
    # Bootstrap logger for the service (run_id=None generates a new UUID)
    logger = bootstrap_logger(
        pipeline="pipeline_runner_service",
        run_id=None,
        log_level="INFO",
    )

    # Create factory and extractor
    runner_factory = create_runner_factory(registry=registry)
    metrics_extractor = create_metrics_extractor()

    return PipelineRunnerService(
        runner_factory=runner_factory,
        metrics_extractor=metrics_extractor,
        logger=logger,
    )
