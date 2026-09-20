"""Bootstrap functions for pipeline runner service.

Provides bootstrap functions for PipelineRunnerService assembly.
This service provides a unified interface for running pipelines
from any orchestration layer (CLI, REST API, etc.).
"""

from __future__ import annotations

from pathlib import Path

from bioetl.application.observability.control_plane_archive import (
    resolve_control_plane_archive_root,
)
from bioetl.composition.control_plane_archive import archive_successful_run
from bioetl.composition.bootstrap.runtime.run_status import create_run_status_capture

from bioetl.application.services.execution.pipeline_run_context_service import (
    PipelineRunContextService,
)
from bioetl.application.services.execution.pipeline_run_execution_service import (
    PipelineRunExecutionService,
)
from bioetl.application.services.execution.pipeline_runner_models import (
    RunOptions,
    RunResult,
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
from bioetl.infrastructure.storage.run_report_store_adapter import (
    FileRunReportStoreAdapter,
)
from bioetl.infrastructure.time import SystemClock

__all__ = ["bootstrap_pipeline_runner_service"]


def _pipeline_run_id_factory() -> str:
    """Factory function for pipeline run IDs."""
    return str(create_runtime_occurrence_run_id("pipeline_run"))


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
    archive_root = resolve_control_plane_archive_root(
        Path(settings.archive_root) if settings.archive_root is not None else None
    )
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

    def _archive_control_plane(result: RunResult, options: RunOptions | None) -> None:
        # The runner seam ignores the archive outcome; keep the call total.
        archive_successful_run(
            result=result,
            options=options,
            data_root=Path(settings.data_dir),
            archive_root=archive_root,
            report_root=settings.report_root,
        )

    return PipelineRunnerService(
        report_store=FileRunReportStoreAdapter(),
        report_root=settings.report_root,
        capture_control_plane=create_run_status_capture(
            settings.data_dir,
            archive_root=archive_root,
            report_root=settings.report_root,
        ),
        archive_control_plane=_archive_control_plane,
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
