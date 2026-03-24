"""File-backed run-manifest persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from bioetl.domain.control_plane import RunManifest
from bioetl.domain.ports import RunManifestPort
from bioetl.domain.types import RunID

__all__ = ["FileRunManifestStore"]


@dataclass(slots=True)
class FileRunManifestStore(RunManifestPort):
    """Persist manifests as JSON files under the control-plane output tree."""

    base_path: Path

    def save(self, manifest: RunManifest) -> None:
        """Persist manifest JSON and run-id index."""
        manifest_path = self.base_path / f"{manifest.manifest_id}.json"
        run_index_dir = self.base_path / "_by_run_id"
        run_index_path = run_index_dir / f"{manifest.run_id}.txt"

        self.base_path.mkdir(parents=True, exist_ok=True)
        run_index_dir.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(manifest.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        run_index_path.write_text(manifest.manifest_id, encoding="utf-8")

    def get(self, manifest_id: str) -> RunManifest | None:
        """Load a manifest by identifier if present."""
        manifest_path = self.base_path / f"{manifest_id}.json"
        if not manifest_path.exists():
            return None
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Manifest payload must be a JSON object")
        return RunManifest.from_dict(payload)

    def get_by_run_id(self, run_id: RunID) -> RunManifest | None:
        """Resolve run-id index to manifest identifier."""
        run_index_path = self.base_path / "_by_run_id" / f"{run_id}.txt"
        if not run_index_path.exists():
            return None
        manifest_id = run_index_path.read_text(encoding="utf-8").strip()
        if not manifest_id:
            return None
        return self.get(manifest_id)
