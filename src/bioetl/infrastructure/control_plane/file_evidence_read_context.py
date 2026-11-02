"""Read-only control-plane context bound to one resolved evidence data root."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

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

__all__ = ["FileEvidenceReadContext"]


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

    def get_manifest_by_run_id(self, run_id: RunID) -> RunManifest | None:
        """Delegate to the bound ``RunManifestPort.get_by_run_id``."""
        self._validate_bound_paths()
        return self.manifest_port.get_by_run_id(run_id)

    def get_workflow_manifest_by_run_id(self, run_id: RunID) -> WorkflowManifest | None:
        """Delegate to the workflow manifest store bound to this data root."""
        self._validate_bound_paths()
        return self.workflow_manifest_port.get_by_run_id(run_id)

    def verify_replay_objects(self, manifest: RunManifest) -> Mapping[str, bool]:
        """Re-check config / lock / Bronze bytes; never cache READY forever."""
        self._validate_bound_paths()
        return self.replay_object_verifier.verify(manifest)

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
        _validate_control_tree(current_root, trusted_base=self.trusted_alias_base)


def _validate_control_tree(data_root: Path, *, trusted_base: Path) -> None:
    """Reject linked standard control/data roots before binding file stores."""
    roots = (
        data_root / "output",
        data_root / "output" / "control",
        data_root / "output" / "control" / "run_manifest",
        data_root / "output" / "control" / "run_ledger",
        data_root / "output" / "control" / "workflow_manifest",
        data_root / "output" / "control" / "lineage",
        data_root / "output" / "control" / "effective_config",
        data_root / "output" / "control" / "dependency_locks",
        data_root / "output" / "bronze",
    )
    for root in roots:
        assert_path_within_trusted_base(
            root,
            trusted_base=trusted_base,
            field_name="control-plane evidence path",
        )
