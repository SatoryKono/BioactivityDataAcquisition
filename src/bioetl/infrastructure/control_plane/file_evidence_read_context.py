"""Read-only control-plane context bound to one resolved evidence data root."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar, cast
from uuid import UUID

from bioetl.domain.control_plane import RunManifest, WorkflowManifest
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
