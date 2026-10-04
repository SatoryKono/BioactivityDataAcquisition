"""Compose parent report persistence with the configured evidence stores."""

from pathlib import Path

from bioetl.application.services.execution.pipeline_runner_models import RunResult
from bioetl.application.services.run_reports.composite import CompositeRunReportService
from bioetl.composition.control_plane_archive import archive_successful_run
from bioetl.composition.bootstrap.runtime.run_status import create_run_status_capture
from bioetl.composition.runtime_builders.config_access import get_settings
from bioetl.domain.ports import LoggerPort
from bioetl.infrastructure.storage.run_report_store_adapter import (
    FileRunReportStoreAdapter,
)
from bioetl.infrastructure.time import SystemClock
from bioetl.infrastructure.adapters.http.health import provider_execution_scope
from bioetl.composition.bootstrap.runtime.assay_replay_evidence import replay_artifacts


def create_composite_reporter(
    *, pipeline_name: str, manifest_id: str | None, logger: LoggerPort
) -> CompositeRunReportService:
    settings = get_settings()

    def archive(result: RunResult) -> None:
        archive_successful_run(
            result=result,
            options=None,
            data_root=Path(settings.data_dir),
            archive_root=Path(settings.archive_root)
            if settings.archive_root is not None
            else None,
            report_root=settings.report_root,
        )

    return CompositeRunReportService(
        pipeline_name=pipeline_name,
        manifest_id=manifest_id,
        store=FileRunReportStoreAdapter(),
        root=settings.report_root,
        clock=SystemClock(),
        logger=logger,
        archive=archive,
        execution_scope=provider_execution_scope,
        replay_artifacts=lambda run_id: replay_artifacts(
            settings.report_root, pipeline_name, run_id
        ),
        capture=create_run_status_capture(
            settings.data_dir,
            report_root=settings.report_root,
            archive_root=Path(settings.archive_root)
            if settings.archive_root is not None
            else None,
        ),
    )
