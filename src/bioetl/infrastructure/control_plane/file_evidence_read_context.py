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
from bioetl.infrastructure.control_plane.file_lineage_store import FileLineageStore
from bioetl.infrastructure.control_plane.file_run_ledger_store import FileRunLedgerStore
from bioetl.infrastructure.control_plane.file_run_manifest_store import (
    FileRunManifestStore,
)
from bioetl.infrastructure.control_plane.file_workflow_manifest_store import (
    FileWorkflowManifestStore,
)
from bioetl.infrastructure.control_plane.replay_object_verifier import (
    ReplayObjectVerifier,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort
    from bioetl.domain.ports.control_plane.lineage import LineageStorePort
    from bioetl.domain.ports.control_plane.run_ledger import RunLedgerPort
    from bioetl.domain.ports.control_plane.run_manifest import RunManifestPort
    from bioetl.domain.ports.control_plane.workflow_manifest import (
        WorkflowManifestPort,
    )

__all__ = [
    "FileEvidenceReadContext",
    "FileEvidenceReadContextFactory",
]


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
        self._assert_concrete_run_index(
            self.data_root / "output" / "control" / "run_manifest",
            run_id,
            suffix=".json",
        )
        return self.manifest_port.get_by_run_id(run_id)

    def get_workflow_manifest_by_run_id(self, run_id: RunID) -> WorkflowManifest | None:
        """Delegate to the workflow manifest store bound to this data root."""
        self._validate_bound_paths()
        self._assert_concrete_run_index(
            self.data_root / "output" / "control" / "workflow_manifest",
            run_id,
            suffix=".json",
        )
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
        _validate_control_tree(
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
            manifest_id = index_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise EvidenceLocationInvalidError(
                "control-plane run index is not readable within the trusted base"
            ) from exc
        if not manifest_id:
            return
        record_path = store_base / f"{manifest_id}{suffix}"
        assert_path_within_trusted_base(
            record_path,
            trusted_base=self.trusted_alias_base,
            field_name="control-plane manifest record path",
        )


@dataclass(frozen=True, slots=True)
class FileEvidenceReadContextFactory:
    """Open file-backed read ports under a trusted alias base (RF-003)."""

    metrics: MetricsPort | None = None

    def open(
        self,
        data_root: Path,
        *,
        trusted_alias_base: Path,
    ) -> FileEvidenceReadContext:
        """Validate containment, then bind standard control-plane file stores."""
        alias_base = Path(trusted_alias_base).resolve(strict=False)
        safe_root = assert_path_within_trusted_base(
            Path(data_root),
            trusted_base=alias_base,
            field_name="data_root",
        )
        _validate_control_tree(safe_root, trusted_alias_base=alias_base)
        output_root = safe_root / "output" / "control"
        verifier = ReplayObjectVerifier(
            config_root=output_root / "effective_config",
            lock_root=output_root / "dependency_locks",
            bronze_root=safe_root / "output" / "bronze",
            trusted_base=alias_base,
        )
        return FileEvidenceReadContext(
            data_root=safe_root,
            trusted_alias_base=alias_base,
            manifest_port=FileRunManifestStore(
                base_path=output_root / "run_manifest",
                metrics=self.metrics,
                replay_object_verifier=verifier,
            ),
            ledger_port=FileRunLedgerStore(
                base_path=output_root / "run_ledger",
                metrics=self.metrics,
            ),
            workflow_manifest_port=FileWorkflowManifestStore(
                base_path=output_root / "workflow_manifest",
                metrics=self.metrics,
            ),
            lineage_port=FileLineageStore(
                base_path=output_root / "lineage",
                metrics=self.metrics,
            ),
            replay_object_verifier=verifier,
        )


def _validate_control_tree(
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
        data_root / "output" / "control" / "dependency_locks",
        data_root / "output" / "bronze",
    )
    for root in roots:
        assert_path_within_trusted_base(
            root,
            trusted_base=trusted_alias_base,
            field_name="control-plane evidence path",
        )
