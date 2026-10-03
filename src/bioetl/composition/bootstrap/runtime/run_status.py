"""Composition of persisted run-status capture using existing local stores."""

from __future__ import annotations

from pathlib import Path
from collections.abc import Callable
from bioetl.application.services.control_plane.manifest.contract_evidence import (
    build_runtime_contract_evidence,
)
from bioetl.infrastructure.control_plane.file_contract_evidence_recorder import (
    FileContractEvidenceRecorder,
)
from bioetl.application.services.execution.pipeline_runner_models import RunResult
from bioetl.application.services.run_reports.composite import CompositeRunReportService
from bioetl.composition.runtime_builders.config_access import get_settings
from bioetl.domain.ports import LoggerPort
from bioetl.infrastructure.storage.run_report_store_adapter import (
    FileRunReportStoreAdapter,
)
from bioetl.infrastructure.control_plane.file_run_manifest_store import (
    FileRunManifestStore,
)
from bioetl.infrastructure.time import SystemClock
from bioetl.composition.control_plane_archive import archive_successful_run
from bioetl.composition.bootstrap.runtime.run_status_capture import (
    create_run_status_capture as create_run_status_capture,
)


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
        capture=create_run_status_capture(
            settings.data_dir,
            report_root=settings.report_root,
            archive_root=Path(settings.archive_root)
            if settings.archive_root is not None
            else None,
        ),
    )


def create_composite_contract_finalizer(
    *,
    pipeline_name: str,
    manifest_id: str,
) -> Callable[[str, bool], None]:
    root = Path(get_settings().data_dir) / "output/control/run_manifest"
    store = FileRunManifestStore(base_path=root)
    recorder = FileContractEvidenceRecorder(base_path=root)

    def finalize(run_id: str, resume_requested: bool) -> None:
        manifest = store.get(manifest_id)
        if manifest is None:
            raise RuntimeError("Composite contract manifest is missing")
        if str(manifest.run_id) != run_id or manifest.pipeline_name != pipeline_name:
            raise RuntimeError("Composite contract manifest identity mismatch")
        provenance = manifest.code_provenance
        recorder.record(
            manifest_id,
            build_runtime_contract_evidence(
                manifest_id=manifest_id,
                contract_ref=provenance.contract_ref,
                contract_schema_hash=provenance.contract_schema_hash,
                resume_requested=resume_requested,
                lock_owner_id=run_id,
            ),
        )

    return finalize
