"""File-backed effective-config artifact persistence."""

from __future__ import annotations

import json
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from bioetl.domain.types import RunID
from bioetl.infrastructure.storage.atomic import atomic_write_text

__all__ = ["FileEffectiveConfigArtifactStore"]


@dataclass(slots=True)
class FileEffectiveConfigArtifactStore:
    """Persist effective-config artifacts as JSON files under control-plane."""

    base_path: Path

    def save(
        self, *, artifact_id: str, run_id: RunID, payload: dict[str, object]
    ) -> None:
        """Persist artifact payload and maintain run-id index."""
        artifact_path = self.base_path / f"{artifact_id}.json"
        run_index_dir = self.base_path / "_by_run_id"
        run_index_path = run_index_dir / f"{run_id}.txt"
        failed_path = artifact_path

        self.base_path.mkdir(parents=True, exist_ok=True)
        run_index_dir.mkdir(parents=True, exist_ok=True)
        try:
            atomic_write_text(
                artifact_path,
                json.dumps(payload, indent=2, sort_keys=True),
            )
            failed_path = run_index_path
            atomic_write_text(run_index_path, artifact_id)
        except (OSError, TypeError, ValueError):
            if failed_path == run_index_path:
                self._rollback_artifact_file(artifact_path)
            raise

    def get(self, artifact_id: str) -> dict[str, object] | None:
        """Load one artifact payload by identifier."""
        artifact_path = self.base_path / f"{artifact_id}.json"
        if not artifact_path.exists():
            return None
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Effective-config artifact payload must be a JSON object")
        return {str(key): value for key, value in payload.items()}

    def get_by_run_id(self, run_id: RunID) -> dict[str, object] | None:
        """Resolve run-id index to artifact identifier and load payload."""
        run_index_path = self.base_path / "_by_run_id" / f"{run_id}.txt"
        if not run_index_path.exists():
            return None
        artifact_id = run_index_path.read_text(encoding="utf-8").strip()
        if not artifact_id:
            return None
        return self.get(artifact_id)

    @staticmethod
    def _rollback_artifact_file(artifact_path: Path) -> None:
        """Remove a persisted artifact file when a later consistency step fails."""
        with suppress(OSError):
            if artifact_path.exists():
                artifact_path.unlink()
