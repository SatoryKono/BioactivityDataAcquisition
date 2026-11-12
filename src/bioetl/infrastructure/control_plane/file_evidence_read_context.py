"""Read-only control-plane context bound to one resolved evidence data root."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar, cast
from uuid import UUID

from bioetl.domain.control_plane import RunLedgerEntry, RunManifest, WorkflowManifest
from bioetl.domain.control_plane.run_evidence_location import (
    EvidenceLocationInvalidError,
)
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane.evidence_location_path_safety import (
    assert_path_within_trusted_base,
)
from bioetl.infrastructure.control_plane.replay_object_verifier import (
    ReplayObjectVerifier,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        LineageStorePort,
        RunLedgerPort,
        RunManifestPort,
        WorkflowManifestPort,
    )

__all__ = [
    "FileEvidenceReadContext",
    "validate_control_tree",
]

# Shared Sonar-safe suffix for control-plane JSON records (manifest / config).
_CONTROL_PLANE_JSON_RECORD_SUFFIX = ".json"

_TBoundRecord = TypeVar("_TBoundRecord")


def _coerce_run_id(run_id: object) -> RunID:
    """Normalize string/UUID run ids to ``RunID`` at the file-adapter boundary.

    ``resolve()`` / ``load_manifest()`` accept string ownership keys; file stores
    compare against deserialized UUID ``RunID`` values. Coerce here so the same
    logical id does not fail the index identity check as a string.
    """
    if isinstance(run_id, UUID):
        return cast(RunID, run_id)
    return cast(RunID, UUID(str(run_id)))


@dataclass(frozen=True, slots=True)
class FileEvidenceReadContext:
    """Consistent read-only stores for one selected data root."""

    data_root: Path
    trusted_alias_base: Path
    manifest_port: RunManifestPort
    ledger_port: RunLedgerPort
    workflow_manifest_port: WorkflowManifestPort
    lineage_port: LineageStorePort
    replay_object_verifier: ReplayObjectVerifier
    validation_service: object | None = None

    def get_validation_service(self) -> object | None:
        """Return validation ports composed for this same resolved data root."""
        self._validate_bound_paths()
        return self.validation_service

    def get_manifest_by_run_id(self, run_id: object) -> RunManifest | None:
        """Delegate to the bound ``RunManifestPort.get_by_run_id``."""
        return self._get_bound_record_by_run_id(
            run_id,
            store_dir="run_manifest",
            loader=self.manifest_port.get_by_run_id,
        )

    def get_workflow_manifest_by_run_id(
        self, run_id: object
    ) -> WorkflowManifest | None:
        """Delegate to the workflow manifest store bound to this data root."""
        return self._get_bound_record_by_run_id(
            run_id,
            store_dir="workflow_manifest",
            loader=self.workflow_manifest_port.get_by_run_id,
        )

    def get_ledger_entries_by_run_id(
        self, run_id: object
    ) -> tuple[RunLedgerEntry, ...]:
        """Contain ledger indexes and predecessor files before reading any bytes."""
        normalized = _coerce_run_id(run_id)
        self._validate_bound_paths()
        base = self.data_root / "output" / "control" / "run_ledger"
        index = base / "_by_run_id" / f"{normalized}.txt"
        assert_path_within_trusted_base(
            index, trusted_base=self.data_root, field_name="ledger run index"
        )
        record_id = index.read_text(encoding="utf-8").strip() if index.exists() else ""
        seen: set[str] = set()
        # Validate only the selected successor chain. No unrelated ledger scan,
        # and no read outside this run's root even within a shared trusted alias.
        while record_id and record_id not in seen:
            seen.add(record_id)
            assert_path_within_trusted_base(
                base / f"{record_id}.jsonl",
                trusted_base=self.data_root,
                field_name="ledger record path",
            )
            pointer = base / "_predecessors" / f"{record_id}.txt"
            assert_path_within_trusted_base(
                pointer, trusted_base=self.data_root, field_name="ledger predecessor"
            )
            record_id = (
                pointer.read_text(encoding="utf-8").strip() if pointer.exists() else ""
            )
        return tuple(self.ledger_port.list_entries_by_run_id(normalized))

    def _get_bound_record_by_run_id(
        self,
        run_id: object,
        *,
        store_dir: str,
        loader: Callable[[RunID], _TBoundRecord | None],
    ) -> _TBoundRecord | None:
        """Coerce id, contain the concrete index, then load via the bound port."""
        normalized = _coerce_run_id(run_id)
        self._validate_bound_paths()
        self._assert_concrete_run_index(
            self.data_root / "output" / "control" / store_dir,
            normalized,
            suffix=_CONTROL_PLANE_JSON_RECORD_SUFFIX,
        )
        return loader(normalized)

    def verify_replay_objects(self, manifest: object) -> Mapping[str, bool]:
        """Re-check config / lock / Bronze bytes; never cache READY forever."""
        self._validate_bound_paths()
        # Index or record symlinks can escape even when the parent stayed inside.
        bound = cast(RunManifest, manifest)
        self._assert_concrete_run_index(
            self.data_root / "output" / "control" / "effective_config",
            bound.run_id,
            suffix=_CONTROL_PLANE_JSON_RECORD_SUFFIX,
        )
        return self.replay_object_verifier.verify(bound)

    def _validate_bound_paths(self) -> None:
        """Recheck the alias and child store trees at each read boundary."""
        current_root = assert_path_within_trusted_base(
            self.data_root,
            trusted_base=self.trusted_alias_base,
            field_name="data_root",
        )
        if current_root != self.data_root:
            raise EvidenceLocationInvalidError(
                "data_root changed after the read context was opened"
            )
        validate_control_tree(
            current_root,
            trusted_alias_base=self.trusted_alias_base,
        )

    def _assert_concrete_run_index(
        self,
        store_base: Path,
        run_id: RunID,
        *,
        suffix: str,
    ) -> None:
        """Contain concrete ``_by_run_id`` index + target record under alias base.

        Directory-root checks alone miss outward symlinks on index files or
        ``<id>.json`` records that escape the trusted tree.
        """
        index_path = store_base / "_by_run_id" / f"{run_id}.txt"
        assert_path_within_trusted_base(
            index_path,
            trusted_base=self.trusted_alias_base,
            field_name="control-plane run index path",
        )
        try:
            if not index_path.exists():
                return
            record_id = index_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise EvidenceLocationInvalidError(
                "control-plane run index is not readable within the trusted base"
            ) from exc
        if not record_id:
            return
        record_path = store_base / f"{record_id}{suffix}"
        assert_path_within_trusted_base(
            record_path,
            trusted_base=self.trusted_alias_base,
            field_name="control-plane record path",
        )


def validate_control_tree(
    data_root: Path,
    *,
    trusted_alias_base: Path,
) -> None:
    """Reject linked standard control/data roots before binding file stores."""
    roots = (
        data_root / "output",
        data_root / "output" / "control",
        data_root / "output" / "control" / "run_manifest",
        data_root / "output" / "control" / "run_manifest" / "_by_run_id",
        data_root / "output" / "control" / "run_ledger",
        data_root / "output" / "control" / "workflow_manifest",
        data_root / "output" / "control" / "workflow_manifest" / "_by_run_id",
        data_root / "output" / "control" / "lineage",
        data_root / "output" / "control" / "effective_config",
        data_root / "output" / "control" / "effective_config" / "_by_run_id",
        data_root / "output" / "control" / "dependency_locks",
        data_root / "output" / "bronze",
    )
    for root in roots:
        assert_path_within_trusted_base(
            root,
            trusted_base=trusted_alias_base,
            field_name="control-plane evidence path",
        )


@dataclass(frozen=True, slots=True)
class _SelectedRootLedgerPort:
    """Read-only ledger port that contains files under the selected data_root.

    Validation uses the same run-id chain as Processed Records, after each
    concrete JSONL / predecessor pointer is checked against the selected root.
    """

    context: FileEvidenceReadContext

    def append(self, entry: RunLedgerEntry) -> None:
        raise NotImplementedError("selected validation ledger is read-only")

    def list_entries(self, manifest_id: str) -> list[RunLedgerEntry]:
        self._assert_manifest_chain(manifest_id)
        entries = self.context.ledger_port.list_entries(manifest_id)
        if not entries:
            return []
        return list(self.context.get_ledger_entries_by_run_id(entries[0].run_id))

    def list_entries_by_run_id(self, run_id: RunID) -> list[RunLedgerEntry]:
        return list(self.context.get_ledger_entries_by_run_id(run_id))

    def list_entries_after(
        self,
        manifest_id: str,
        after_entry_id: str | None,
    ) -> list[RunLedgerEntry]:
        self._assert_manifest_chain(manifest_id)
        return self.context.ledger_port.list_entries_after(manifest_id, after_entry_id)

    def _assert_manifest_chain(self, manifest_id: str) -> None:
        base = self.context.data_root / "output" / "control" / "run_ledger"
        record_id = manifest_id
        seen: set[str] = set()
        while record_id and record_id not in seen:
            seen.add(record_id)
            assert_path_within_trusted_base(
                base / f"{record_id}.jsonl",
                trusted_base=self.context.data_root,
                field_name="ledger record path",
            )
            pointer = base / "_predecessors" / f"{record_id}.txt"
            assert_path_within_trusted_base(
                pointer,
                trusted_base=self.context.data_root,
                field_name="ledger predecessor",
            )
            record_id = (
                pointer.read_text(encoding="utf-8").strip() if pointer.exists() else ""
            )
