"""Unit tests for RunManifestInspectionService."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from bioetl.application.services.run_manifest_inspection_service import (
    RunManifestInspectionService,
)
from bioetl.domain.control_plane import (
    RunCodeProvenance,
    RunLedgerEntry,
    RunManifest,
)
from bioetl.domain.ports import RunLedgerPort, RunManifestPort
from bioetl.domain.types import RunID, RunType


class _InMemoryRunManifestStore(RunManifestPort):
    def __init__(self) -> None:
        self._items: dict[str, RunManifest] = {}
        self._by_run_id: dict[str, str] = {}

    def save(self, manifest: RunManifest) -> None:
        self._items[manifest.manifest_id] = manifest
        self._by_run_id[str(manifest.run_id)] = manifest.manifest_id

    def get(self, manifest_id: str) -> RunManifest | None:
        return self._items.get(manifest_id)

    def get_by_run_id(self, run_id: RunID) -> RunManifest | None:
        manifest_id = self._by_run_id.get(str(run_id))
        return None if manifest_id is None else self._items.get(manifest_id)


class _InMemoryRunLedgerStore(RunLedgerPort):
    def __init__(self) -> None:
        self._items: list[RunLedgerEntry] = []

    def append(self, entry: RunLedgerEntry) -> None:
        self._items.append(entry)

    def list_entries(self, manifest_id: str) -> list[RunLedgerEntry]:
        return [item for item in self._items if item.manifest_id == manifest_id]

    def list_entries_by_run_id(self, run_id: RunID) -> list[RunLedgerEntry]:
        return [item for item in self._items if item.run_id == run_id]


def _make_manifest(
    *,
    manifest_id: str,
    run_id: RunID,
    run_type: RunType = RunType.INCREMENTAL,
    config_hash: str = "deadbeef",
    limit: int = 100,
) -> RunManifest:
    return RunManifest(
        manifest_id=manifest_id,
        execution_fingerprint=f"fingerprint-{manifest_id}",
        schema_version="1.0",
        created_at=datetime.now(UTC),
        run_id=run_id,
        run_type=run_type,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={"limit": limit},
        runtime_config={"run_type": run_type.value, "limit": limit},
        resolved_config={"provider": "chembl", "entity_type": "activity"},
        code_provenance=RunCodeProvenance(
            pipeline_version="1.0.0",
            git_commit="abc1234",
            config_hash=config_hash,
        ),
    )


def test_show_resolves_manifest_by_run_id_and_includes_ledger_history() -> None:
    manifest_store = _InMemoryRunManifestStore()
    ledger_store = _InMemoryRunLedgerStore()
    run_id = RunID(uuid4())
    manifest = _make_manifest(manifest_id="manifest-1", run_id=run_id)
    manifest_store.save(manifest)
    ledger_entry = RunLedgerEntry(
        entry_id="entry-1",
        manifest_id="manifest-1",
        run_id=run_id,
        event_type="run_finished",
        occurred_at=datetime.now(UTC),
        status="success",
    )
    ledger_store.append(ledger_entry)
    service = RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    )

    result = service.show(str(run_id))

    assert result.manifest == manifest
    assert result.ledger_entries == (ledger_entry,)


def test_diff_reports_changed_top_level_fields() -> None:
    manifest_store = _InMemoryRunManifestStore()
    left_run_id = RunID(uuid4())
    right_run_id = RunID(uuid4())
    left = _make_manifest(
        manifest_id="manifest-left",
        run_id=left_run_id,
        run_type=RunType.INCREMENTAL,
        config_hash="hash-left",
        limit=100,
    )
    right = _make_manifest(
        manifest_id="manifest-right",
        run_id=right_run_id,
        run_type=RunType.REBUILD,
        config_hash="hash-right",
        limit=500,
    )
    manifest_store.save(left)
    manifest_store.save(right)
    service = RunManifestInspectionService(manifest_port=manifest_store)

    result = service.diff("manifest-left", "manifest-right")

    diff_fields = {entry.field for entry in result.differences}
    assert result.left_manifest_id == "manifest-left"
    assert result.right_manifest_id == "manifest-right"
    assert "manifest_id" in diff_fields
    assert "run_id" in diff_fields
    assert "run_type" in diff_fields
    assert "launch_context" in diff_fields
    assert "runtime_config" in diff_fields
    assert "code_provenance" in diff_fields
