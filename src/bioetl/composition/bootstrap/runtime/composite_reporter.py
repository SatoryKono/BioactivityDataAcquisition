"""Compose parent report persistence with the configured evidence stores."""

from bioetl.application.services.run_reports.composite import CompositeRunReportService
from bioetl.composition.bootstrap.runtime.run_status import create_run_status_capture
from bioetl.composition.runtime_builders.config_access import get_settings
from bioetl.domain.ports import LoggerPort
from bioetl.infrastructure.storage.run_report_store_adapter import (
    FileRunReportStoreAdapter,
)
from bioetl.infrastructure.time import SystemClock


def create_composite_reporter(
    *, pipeline_name: str, manifest_id: str | None, logger: LoggerPort
) -> CompositeRunReportService:
    settings = get_settings()
    return CompositeRunReportService(
        pipeline_name=pipeline_name,
        manifest_id=manifest_id,
        store=FileRunReportStoreAdapter(),
        root=settings.report_root,
        clock=SystemClock(),
        logger=logger,
        capture=create_run_status_capture(
            settings.data_dir, report_root=settings.report_root
        ),
    )
