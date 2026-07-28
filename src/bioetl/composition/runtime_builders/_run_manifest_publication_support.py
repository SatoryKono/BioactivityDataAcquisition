"""Private publication helpers for run-manifest persistence."""

from __future__ import annotations

from typing import TYPE_CHECKING
from bioetl.application.services.control_plane.ledger.service import (
    RunLedgerService,
)
from bioetl.application.services.control_plane.manifest.service import (
    RunManifestCreateSpec,
    RunManifestService,
)
from bioetl.composition.bootstrap.control_plane_store_builders import (
    create_run_manifest_store,
)
from bioetl.composition.occurrence_identity import create_runtime_occurrence_id
from bioetl.domain.control_plane import RunManifest
from bioetl.infrastructure.time import SystemClock

if TYPE_CHECKING:
    from bioetl.composition.runtime_builders.runner_inputs import RunnerInputs
    from bioetl.infrastructure.control_plane import FileRunManifestStore

def create_manifest_store(inputs: RunnerInputs) -> FileRunManifestStore:
    """Create the file-backed run-manifest store."""
    return create_run_manifest_store(
        settings=inputs.settings,
        metrics=inputs.observability.metrics,
    )

def create_manifest_record(
    *,
    manifest_store: FileRunManifestStore,
    manifest_create_request: RunManifestCreateSpec,
    ledger_service: RunLedgerService | None,
) -> RunManifest:
    """Create and optionally ledger-record one manifest."""
    manifest = RunManifestService(
        manifest_port=manifest_store,
        clock=SystemClock(),
        _manifest_id_factory=lambda: create_runtime_occurrence_id("run_manifest"),
    ).create_manifest(manifest_create_request)
    if ledger_service is not None:
        ledger_service.manifest_id = manifest.manifest_id
        ledger_service.record_manifest_created(manifest)
    return manifest
