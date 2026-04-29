"""File-backed effective-config artifact persistence."""

from __future__ import annotations

import json
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from bioetl.domain.types import RunID
from bioetl.infrastructure.storage.atomic import AtomicWriteError, atomic_write_text

__all__ = [
    "EffectiveConfigArtifactConflictError",
    "FileEffectiveConfigArtifactStore",
]

_OCCURRENCE_DIR = "_occurrences"
_OCCURRENCE_ENVELOPE_KEY = "occurrence_envelope"
_RUN_INDEX_DIR = "_by_run_id"
_SEMANTIC_ARTIFACT_KEY = "semantic_artifact"


class EffectiveConfigArtifactConflictError(ValueError):
    """Raised when an existing semantic artifact has conflicting content."""


@dataclass(slots=True)
class FileEffectiveConfigArtifactStore:
    """Persist effective-config artifacts as JSON files under control-plane."""

    base_path: Path

    def save(
        self, *, artifact_id: str, run_id: RunID, payload: dict[str, object]
    ) -> None:
        """Persist immutable semantic payload and maintain occurrence indexes."""
        artifact_path = self.base_path / f"{artifact_id}.json"
        occurrence_dir = self.base_path / _OCCURRENCE_DIR
        occurrence_path = occurrence_dir / f"{run_id}.json"
        run_index_dir = self.base_path / _RUN_INDEX_DIR
        run_index_path = run_index_dir / f"{run_id}.txt"
        artifact_created = False
        occurrence_created = False

        self.base_path.mkdir(parents=True, exist_ok=True)
        occurrence_dir.mkdir(parents=True, exist_ok=True)
        run_index_dir.mkdir(parents=True, exist_ok=True)
        try:
            artifact_created = self._save_semantic_artifact(
                artifact_path=artifact_path,
                artifact_id=artifact_id,
                payload=payload,
            )
            atomic_write_text(
                occurrence_path,
                _to_stable_json(
                    _build_occurrence_payload(
                        artifact_id=artifact_id,
                        run_id=run_id,
                        payload=payload,
                    )
                ),
            )
            occurrence_created = True
            atomic_write_text(run_index_path, artifact_id)
        except (AtomicWriteError, OSError, TypeError, ValueError):
            if occurrence_created:
                self._rollback_file(occurrence_path)
            if artifact_created:
                self._rollback_artifact_file(artifact_path)
            raise

    def get(self, artifact_id: str) -> dict[str, object] | None:
        """Load one artifact payload by identifier."""
        artifact_path = self.base_path / f"{artifact_id}.json"
        if not artifact_path.exists():
            return None
        return _read_json_object(artifact_path)

    def get_by_run_id(self, run_id: RunID) -> dict[str, object] | None:
        """Resolve run-id index to artifact identifier and load payload."""
        run_index_path = self.base_path / _RUN_INDEX_DIR / f"{run_id}.txt"
        if not run_index_path.exists():
            return None
        artifact_id = run_index_path.read_text(encoding="utf-8").strip()
        if not artifact_id:
            return None
        return self.get(artifact_id)

    def get_occurrence_by_run_id(self, run_id: RunID) -> dict[str, object] | None:
        """Load occurrence metadata for one run identifier."""
        occurrence_path = self.base_path / _OCCURRENCE_DIR / f"{run_id}.json"
        if not occurrence_path.exists():
            return None
        return _read_json_object(occurrence_path)

    def diff_occurrences_by_run_id(
        self,
        left_run_id: RunID,
        right_run_id: RunID,
    ) -> dict[str, object]:
        """Compare semantic and occurrence identity for two effective configs."""
        left_artifact = self.get_by_run_id(left_run_id)
        right_artifact = self.get_by_run_id(right_run_id)
        left_occurrence = self.get_occurrence_by_run_id(left_run_id)
        right_occurrence = self.get_occurrence_by_run_id(right_run_id)
        semantic_equivalent = (
            left_artifact is not None
            and right_artifact is not None
            and _to_stable_json(left_artifact) == _to_stable_json(right_artifact)
        )
        occurrence_differences = _diff_occurrence_payloads(
            left_occurrence,
            right_occurrence,
        )
        return {
            "left_run_id": str(left_run_id),
            "right_run_id": str(right_run_id),
            "left_artifact_present": left_artifact is not None,
            "right_artifact_present": right_artifact is not None,
            "left_occurrence_present": left_occurrence is not None,
            "right_occurrence_present": right_occurrence is not None,
            "semantic_equivalent": semantic_equivalent,
            "occurrence_only": semantic_equivalent and bool(occurrence_differences),
            "differences": occurrence_differences,
        }

    def _save_semantic_artifact(
        self,
        *,
        artifact_path: Path,
        artifact_id: str,
        payload: dict[str, object],
    ) -> bool:
        """Write semantic artifact once and reject conflicting rewrites."""
        semantic_payload = _build_semantic_payload(
            artifact_id=artifact_id,
            payload=payload,
        )
        semantic_text = _to_stable_json(semantic_payload)
        if artifact_path.exists():
            existing_payload = _read_json_object(artifact_path)
            existing_semantic_payload = _build_semantic_payload(
                artifact_id=artifact_id,
                payload=existing_payload,
            )
            if _to_stable_json(existing_semantic_payload) == semantic_text:
                return False
            raise EffectiveConfigArtifactConflictError(
                "Effective-config semantic artifact already exists with "
                f"different content: {artifact_id}"
            )
        atomic_write_text(artifact_path, semantic_text)
        return True

    @staticmethod
    def _rollback_artifact_file(artifact_path: Path) -> None:
        """Remove a persisted artifact file when a later consistency step fails."""
        FileEffectiveConfigArtifactStore._rollback_file(artifact_path)

    @staticmethod
    def _rollback_file(path: Path) -> None:
        """Remove a file created during a failed multi-file write."""
        with suppress(OSError):
            if path.exists():
                path.unlink()


def _to_stable_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _read_json_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Effective-config artifact payload must be a JSON object")
    return {str(key): value for key, value in payload.items()}


def _build_semantic_payload(
    *,
    artifact_id: str,
    payload: dict[str, object],
) -> dict[str, object]:
    """Return the immutable semantic record persisted by artifact id."""
    semantic_artifact = payload.get(_SEMANTIC_ARTIFACT_KEY)
    if not isinstance(semantic_artifact, dict):
        return {str(key): value for key, value in payload.items()}

    semantic_payload: dict[str, object] = {
        "artifact_id": payload.get("artifact_id", artifact_id),
        _SEMANTIC_ARTIFACT_KEY: semantic_artifact,
    }
    schema_version = payload.get("schema_version")
    if schema_version is None:
        schema_version = semantic_artifact.get("schema_version")
    if schema_version is not None:
        semantic_payload["schema_version"] = schema_version
    return semantic_payload


def _build_occurrence_payload(
    *,
    artifact_id: str,
    run_id: RunID,
    payload: dict[str, object],
) -> dict[str, object]:
    """Return the run-specific occurrence record persisted by run id."""
    occurrence_envelope = payload.get(_OCCURRENCE_ENVELOPE_KEY)
    if not isinstance(occurrence_envelope, dict):
        occurrence_envelope = {}
    occurrence_payload: dict[str, object] = {
        "artifact_id": artifact_id,
        "run_id": str(run_id),
        _OCCURRENCE_ENVELOPE_KEY: occurrence_envelope,
    }
    schema_version = payload.get("schema_version")
    if schema_version is not None:
        occurrence_payload["schema_version"] = schema_version
    return occurrence_payload


def _flatten_occurrence_payload(payload: dict[str, object] | None) -> dict[str, object]:
    """Flatten occurrence payload fields into stable diff paths."""
    if payload is None:
        return {}
    flattened = {
        key: value
        for key, value in payload.items()
        if key != _OCCURRENCE_ENVELOPE_KEY
    }
    occurrence_envelope = payload.get(_OCCURRENCE_ENVELOPE_KEY)
    if isinstance(occurrence_envelope, dict):
        for key, value in sorted(occurrence_envelope.items()):
            flattened[f"{_OCCURRENCE_ENVELOPE_KEY}.{key}"] = value
    return flattened


def _diff_occurrence_payloads(
    left: dict[str, object] | None,
    right: dict[str, object] | None,
) -> list[dict[str, object]]:
    """Return field-level occurrence differences for operator diagnostics."""
    left_flat = _flatten_occurrence_payload(left)
    right_flat = _flatten_occurrence_payload(right)
    differences: list[dict[str, object]] = []
    for field in sorted(set(left_flat) | set(right_flat)):
        left_value = left_flat.get(field)
        right_value = right_flat.get(field)
        if left_value == right_value:
            continue
        differences.append(
            {
                "field": field,
                "left": left_value,
                "right": right_value,
            }
        )
    return differences
