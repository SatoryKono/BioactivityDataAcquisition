"""Shared in-memory fakes for control-plane ports."""

from __future__ import annotations

from bioetl.domain.control_plane import RunLedgerEntry, RunManifest, WorkflowManifest
from bioetl.domain.ports import RunLedgerPort, RunManifestPort, WorkflowManifestPort
from bioetl.domain.types import RunID, RunType

__all__ = [
    "InMemoryRunLedgerStore",
    "InMemoryRunManifestStore",
    "InMemoryWorkflowManifestStore",
]


class InMemoryRunManifestStore(RunManifestPort):
    def __init__(self) -> None:
        self._items: dict[str, RunManifest] = {}
        self._by_run_id: dict[str, str] = {}

    @property
    def items(self) -> dict[str, RunManifest]:
        return self._items

    def save(self, manifest: RunManifest) -> None:
        self._items[manifest.manifest_id] = manifest
        self._by_run_id[str(manifest.run_id)] = manifest.manifest_id

    def get(self, manifest_id: str) -> RunManifest | None:
        return self._items.get(manifest_id)

    def get_by_run_id(self, run_id: RunID) -> RunManifest | None:
        manifest_id = self._by_run_id.get(str(run_id))
        return None if manifest_id is None else self._items.get(manifest_id)

    def get_latest_for_scope(
        self,
        pipeline_name: str,
        run_types: tuple[RunType, ...] = (),
    ) -> RunManifest | None:
        candidates = tuple(
            manifest
            for manifest in self._items.values()
            if manifest.pipeline_name == pipeline_name
            and (not run_types or manifest.run_type in run_types)
        )
        return (
            max(
                candidates,
                key=lambda manifest: (manifest.created_at, manifest.manifest_id),
            )
            if candidates
            else None
        )

    def list_all(self) -> tuple[RunManifest, ...]:
        return tuple(
            sorted(
                self._items.values(),
                key=lambda manifest: (manifest.created_at, manifest.manifest_id),
            )
        )


class InMemoryWorkflowManifestStore(WorkflowManifestPort):
    def __init__(self) -> None:
        self._items: dict[str, WorkflowManifest] = {}
        self._by_run_id: dict[str, str] = {}

    def save(self, manifest: WorkflowManifest) -> None:
        self._items[manifest.manifest_id] = manifest
        self._by_run_id[str(manifest.workflow_run_id)] = manifest.manifest_id

    def get(self, manifest_id: str) -> WorkflowManifest | None:
        return self._items.get(manifest_id)

    def get_by_run_id(self, workflow_run_id: RunID) -> WorkflowManifest | None:
        manifest_id = self._by_run_id.get(str(workflow_run_id))
        return None if manifest_id is None else self._items.get(manifest_id)

    def list_all(self) -> tuple[WorkflowManifest, ...]:
        return tuple(
            sorted(
                self._items.values(),
                key=lambda manifest: (manifest.created_at, manifest.manifest_id),
            )
        )


class InMemoryRunLedgerStore(RunLedgerPort):
    def __init__(self) -> None:
        self._items: list[RunLedgerEntry] = []

    @property
    def items(self) -> list[RunLedgerEntry]:
        return self._items

    def append(self, entry: RunLedgerEntry) -> None:
        if entry.idempotency_key is not None and any(
            item.manifest_id == entry.manifest_id
            and item.idempotency_key == entry.idempotency_key
            for item in self._items
        ):
            return
        self._items.append(entry)

    def list_entries(self, manifest_id: str) -> list[RunLedgerEntry]:
        return [item for item in self._items if item.manifest_id == manifest_id]

    def list_entries_by_run_id(self, run_id: RunID) -> list[RunLedgerEntry]:
        return [item for item in self._items if item.run_id == run_id]

    def list_entries_after(
        self,
        manifest_id: str,
        after_entry_id: str | None,
    ) -> list[RunLedgerEntry]:
        entries = self.list_entries(manifest_id)
        if after_entry_id is None:
            return entries
        for index, item in enumerate(entries):
            if item.entry_id == after_entry_id:
                return entries[index + 1 :]
        raise ValueError(f"missing watermark {after_entry_id!r}")
