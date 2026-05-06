"""Private publication helpers for run-manifest persistence."""

from __future__ import annotations

from typing import TYPE_CHECKING

import bioetl.composition.runtime_builders._run_manifest_support as _manifest_support
from bioetl.application.services.control_plane.run_ledger_service import (
    RunLedgerService,
)
from bioetl.application.services.control_plane.run_manifest_service import (
    RunManifestCreateSpec,
    RunManifestService,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.infrastructure.control_plane import FileRunManifestStore
from bioetl.infrastructure.time import SystemClock

if TYPE_CHECKING:
    from bioetl.composition.runtime_builders.inputs_resolver import RunnerInputs


def create_manifest_store(inputs: RunnerInputs) -> FileRunManifestStore:
    """Create the file-backed run-manifest store."""
    return FileRunManifestStore(
        base_path=_manifest_support.control_plane_root(inputs.settings, "run_manifest"),
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
    ).create_manifest(manifest_create_request)
    if ledger_service is not None:
        ledger_service.manifest_id = manifest.manifest_id
        ledger_service.record_manifest_created(manifest)
    return manifest
