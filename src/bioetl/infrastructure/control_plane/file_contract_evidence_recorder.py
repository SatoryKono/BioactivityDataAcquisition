"""File adapter for the manifest contract-evidence sidecar port."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from bioetl.infrastructure.control_plane._raw_run_manifest_inspection import (
    persist_contract_evidence,
)
from bioetl.infrastructure.control_plane.live_run_manifest_catalog import (
    copy_contract_evidence_to_live_catalog,
)
from bioetl.infrastructure.storage.atomic import AtomicWriteError

__all__ = ["FileContractEvidenceRecorder"]


@dataclass(slots=True)
class FileContractEvidenceRecorder:
    """Write ``<manifest_id>.contract-evidence.json`` next to the manifest."""

    base_path: Path
    live_catalog: Path | None = None

    def record(self, manifest_id: str, evidence: Mapping[str, object]) -> None:
        """Persist one sidecar, then mirror it onto an already published live manifest."""
        persist_contract_evidence(self.base_path, manifest_id, dict(evidence))
        live_catalog = self.live_catalog
        if live_catalog is None:
            return
        try:
            copy_contract_evidence_to_live_catalog(
                manifest_id,
                source_base=self.base_path,
                live_base=live_catalog,
            )
        except (OSError, AtomicWriteError):
            return
