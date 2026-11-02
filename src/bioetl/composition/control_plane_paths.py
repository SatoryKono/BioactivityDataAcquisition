"""Writable control-plane path helpers and RF-003 evidence read factory."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.composition.runtime_builders.run_manifest_data_roots import (
    resolve_data_root,
)
from bioetl.infrastructure.control_plane.evidence_location_path_safety import (
    assert_path_within_trusted_base,
)
from bioetl.infrastructure.control_plane.file_evidence_read_context import (
    FileEvidenceReadContext,
    validate_control_tree,
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

__all__ = [
    "FileEvidenceReadContextFactory",
    "control_plane_root",
    "resolve_data_root",
]

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort
    from bioetl.infrastructure.config.settings_api import Settings


def control_plane_root(settings: Settings, leaf: str) -> Path:
    """Return the canonical control-plane output root for one leaf namespace."""
    return resolve_data_root(settings) / "output" / "control" / leaf


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
        validate_control_tree(safe_root, trusted_alias_base=alias_base)
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
