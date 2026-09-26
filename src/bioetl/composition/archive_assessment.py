"""Composition wiring for archived run assessments (#11250)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.services.run_reports.observations import (
    bind_run_observations,
    reset_run_observations,
    run_observations,
)
from bioetl.application.services.run_reports.snapshots import publish_snapshot
from bioetl.application.services.run_reports.writer import write_json
from bioetl.composition.bootstrap.runtime.run_status import create_run_status_capture
from bioetl.infrastructure.control_plane.archive_assessment import (
    refresh_archived_assessment as refresh_archived_assessment_impl,
)

if TYPE_CHECKING:
    from bioetl.domain.control_plane import (
        ControlPlaneArtifactLifecyclePlan,
        RunManifest,
    )


def refresh_archived_assessment(
    *,
    data_root: Path,
    archive_root: Path,
    report_root: Path,
    manifest: RunManifest,
    plan: ControlPlaneArtifactLifecyclePlan,
    observed_at: datetime,
) -> tuple[bool | None, str]:
    """Wire report-status capture and publish an archived assessment."""
    return refresh_archived_assessment_impl(
        data_root=data_root,
        archive_root=archive_root,
        report_root=report_root,
        manifest=manifest,
        plan=plan,
        observed_at=observed_at,
        capture_factory=lambda: create_run_status_capture(
            data_root,
            archive_root=archive_root,
            report_root=report_root,
        ),
        bind_observations=bind_run_observations,
        reset_observations=reset_run_observations,
        control_plane_observation=lambda: run_observations()["Control Plane"],
        publish_snapshot=publish_snapshot,
        write_json=write_json,
    )
