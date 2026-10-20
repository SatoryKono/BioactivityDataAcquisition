"""Successor ledger history for run-manifest inspection."""

from __future__ import annotations

from dataclasses import replace
from uuid import UUID

import pytest

from bioetl.application.services.control_plane.manifest.inspection_service import (
    RunManifestInspectionCorruptionError,
    RunManifestInspectionService,
)
from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.types import RunID, RunType
from tests.helpers.control_plane import InMemoryRunLedgerStore, InMemoryRunManifestStore
from tests.unit.application.services.run_manifest_test_support import (
    FIXED_TIME,
    make_run_manifest,
)

pytestmark = pytest.mark.unit

_RUN_ID = RunID(UUID("3432761e-d4eb-511e-a62c-b186b301c758"))


def _manifest(manifest_id: str) -> RunManifest:
    return make_run_manifest(
        manifest_id=manifest_id,
        run_id=_RUN_ID,
        run_type=RunType.INCREMENTAL,
        created_at=FIXED_TIME,
    )


def test_show_includes_predecessor_ledger_events_for_successor() -> None:
    manifest_store = InMemoryRunManifestStore()
    ledger_store = InMemoryRunLedgerStore()
    predecessor = _manifest("manifest-pred")
    successor = replace(
        predecessor,
        manifest_id="manifest-next",
        predecessor_manifest_id="manifest-pred",
    )
    manifest_store.save(predecessor)
    manifest_store.save(successor)
    started = RunLedgerEntry(
        entry_id="entry-started",
        manifest_id="manifest-pred",
        run_id=_RUN_ID,
        event_type="run_started",
        occurred_at=FIXED_TIME,
        status="running",
    )
    finished = RunLedgerEntry(
        entry_id="entry-finished",
        manifest_id="manifest-next",
        run_id=_RUN_ID,
        event_type="run_finished",
        occurred_at=FIXED_TIME,
        status="success",
    )
    ledger_store.append(started)
    ledger_store.append(finished)
    service = RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    )

    result = service.show(str(_RUN_ID))

    assert result.manifest.manifest_id == "manifest-next"
    assert result.ledger_entries == (started, finished)


def test_show_rejects_missing_predecessor() -> None:
    manifest_store = InMemoryRunManifestStore()
    predecessor = _manifest("manifest-pred")
    successor = replace(
        predecessor,
        manifest_id="manifest-next",
        predecessor_manifest_id="manifest-missing",
    )
    manifest_store.save(successor)
    service = RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=InMemoryRunLedgerStore(),
    )

    with pytest.raises(RunManifestInspectionCorruptionError, match="missing"):
        service.show("manifest-next")


def test_show_rejects_corrupt_predecessor_read() -> None:
    class _CorruptPredecessorStore(InMemoryRunManifestStore):
        def get(self, manifest_id: str) -> RunManifest | None:
            if manifest_id == "manifest-pred":
                raise ValueError("index corruption")
            return super().get(manifest_id)

    manifest_store = _CorruptPredecessorStore()
    predecessor = _manifest("manifest-pred")
    successor = replace(
        predecessor,
        manifest_id="manifest-next",
        predecessor_manifest_id="manifest-pred",
    )
    manifest_store.save(successor)
    service = RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=InMemoryRunLedgerStore(),
    )

    with pytest.raises(RunManifestInspectionCorruptionError, match="index corruption"):
        service.show("manifest-next")
