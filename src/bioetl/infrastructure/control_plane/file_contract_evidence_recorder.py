"""File adapter for the manifest contract-evidence sidecar port."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from bioetl.infrastructure.control_plane._raw_run_manifest_inspection import (
    persist_contract_evidence,
)

__all__ = ["FileContractEvidenceRecorder"]


@dataclass(slots=True)
class FileContractEvidenceRecorder:
    """Write ``<manifest_id>.contract-evidence.json`` next to the manifest."""

    base_path: Path

    def record(self, manifest_id: str, evidence: Mapping[str, object]) -> None:
        """Persist one sidecar through the existing infra helper."""
        persist_contract_evidence(self.base_path, manifest_id, dict(evidence))
