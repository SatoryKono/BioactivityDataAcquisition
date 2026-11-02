"""Composition factory for file-backed evidence read contexts (RF-003)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.infrastructure.control_plane.evidence_location_path_safety import (
    assert_path_within_trusted_base,
)
from bioetl.infrastructure.control_plane.file_evidence_read_context import (
    FileEvidenceReadContext,
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

__all__ = ["FileEvidenceReadContextFactory"]


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
        trusted_base = Path(trusted_alias_base).resolve(strict=False)
        output_root = _safe_store_root(
            safe_root, trusted_base, "output/control", "output_root"
        )
        config_root = _safe_store_root(
            output_root, trusted_base, "effective_config", "config_root"
        )
        lock_root = _safe_store_root(
            output_root, trusted_base, "dependency_locks", "lock_root"
        )
        bronze_root = _safe_store_root(
            safe_root, trusted_base, "output/bronze", "bronze_root"
        )
        run_manifest_root = _safe_store_root(
            output_root, trusted_base, "run_manifest", "run_manifest_root"
        )
        run_ledger_root = _safe_store_root(
            output_root, trusted_base, "run_ledger", "run_ledger_root"
        )
        workflow_manifest_root = _safe_store_root(
            output_root,
            trusted_base,
            "workflow_manifest",
            "workflow_manifest_root",
        )
        lineage_root = _safe_store_root(
            output_root, trusted_base, "lineage", "lineage_root"
        )
        _validate_control_tree(safe_root, trusted_base=trusted_base)
        verifier = ReplayObjectVerifier(
            config_root=config_root,
            lock_root=lock_root,
            bronze_root=bronze_root,
        )
        return FileEvidenceReadContext(
            data_root=safe_root,
            trusted_alias_base=trusted_base,
            manifest_port=FileRunManifestStore(
                base_path=run_manifest_root,
                metrics=self.metrics,
                replay_object_verifier=verifier,
            ),
            ledger_port=FileRunLedgerStore(
                base_path=run_ledger_root,
                metrics=self.metrics,
            ),
            workflow_manifest_port=FileWorkflowManifestStore(
                base_path=workflow_manifest_root,
                metrics=self.metrics,
            ),
            lineage_port=FileLineageStore(
                base_path=lineage_root,
                metrics=self.metrics,
            ),
            replay_object_verifier=verifier,
        )


def _safe_store_root(
    data_root: Path,
    trusted_base: Path,
    relative_path: str,
    field_name: str,
) -> Path:
    """Validate a concrete store root against the original alias trust anchor."""
    return assert_path_within_trusted_base(
        data_root.joinpath(*relative_path.split("/")),
        trusted_base=trusted_base,
        field_name=field_name,
    )


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
