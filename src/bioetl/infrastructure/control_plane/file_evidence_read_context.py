"""Read-only control-plane context bound to one resolved evidence data root."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.control_plane import RunManifest
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
        return self.manifest_port.get_by_run_id(run_id)

    def verify_replay_objects(self, manifest: RunManifest) -> Mapping[str, bool]:
        """Re-check config / lock / Bronze bytes; never cache READY forever."""
        return self.replay_object_verifier.verify(manifest)


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
        safe_root = assert_path_within_trusted_base(
            Path(data_root),
            trusted_base=Path(trusted_alias_base),
            field_name="data_root",
        )
        output_root = safe_root / "output" / "control"
        verifier = ReplayObjectVerifier(
            config_root=output_root / "effective_config",
            lock_root=output_root / "dependency_locks",
            bronze_root=safe_root / "output" / "bronze",
        )
        return FileEvidenceReadContext(
            data_root=safe_root,
            trusted_alias_base=Path(trusted_alias_base).resolve(strict=False),
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
