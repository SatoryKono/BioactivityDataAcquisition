"""Idempotent row artifacts and a verified manifest for one completed run."""

from __future__ import annotations

import re
from pathlib import Path
from threading import RLock

from bioetl.domain.entities.target_classification_boundary import (
    TargetClassificationArtifactReference,
    TargetClassificationResult,
)
from bioetl.infrastructure.control_plane.evidence_location_publish import (
    publish_bytes_if_absent,
)
from iuphar_target_class.stage0.io import canonical_json_bytes

from ._evidence_validation import validate_row_artifacts
from ._manifest import checked_bytes, object_document, require_sha256, sha256
from .snapshot_loader import OUTPUT_NAMES


def _segment(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,199}", value) is None:
        raise ValueError("invalid classification run or batch path segment")
    return value


def _write_same(path: Path, payload: bytes) -> None:
    if not publish_bytes_if_absent(path, payload, trusted_base=path.parent):
        if path.read_bytes() != payload:
            raise ValueError("conflicting immutable classification artifact")


def _row_root(
    run_root: Path, result: TargetClassificationResult, batch_id: str
) -> Path:
    row_key = sha256(result.input_row_id.encode("utf-8"))
    path = run_root / "batches" / _segment(batch_id) / "rows" / row_key
    if not path.resolve().is_relative_to(run_root):
        raise ValueError("classification row path escapes artifact root")
    names = [artifact.name for artifact in result.artifacts]
    if len(names) != len(set(names)) or set(names) != OUTPUT_NAMES:
        raise ValueError("classification evidence needs all six unique outputs")
    return path


def _publish_files(
    result: TargetClassificationResult, row_root: Path, run_root: Path
) -> None:
    for artifact in result.artifacts:
        path = row_root / artifact.name
        if not path.resolve().is_relative_to(run_root):
            raise ValueError("classification artifact path escapes run root")
        _write_same(path, artifact.payload)


def _row_manifest(
    path: Path, run_root: Path, run_id: str, profile_hash: str
) -> tuple[str, dict[str, str]]:
    if not path.resolve().is_relative_to(run_root):
        raise ValueError("classification manifest path escapes run root")
    manifest = object_document(path.read_bytes())
    if (
        manifest.get("run_id") != run_id
        or manifest.get("profile_sha256") != profile_hash
    ):
        raise ValueError("classification row belongs to another run or profile")
    row_id, raw_hashes = manifest.get("input_row_id"), manifest.get("artifact_sha256")
    if not isinstance(row_id, str) or not isinstance(raw_hashes, dict):
        raise ValueError("invalid classification row manifest")
    if set(raw_hashes) != OUTPUT_NAMES:
        raise ValueError("classification row evidence is incomplete")
    return row_id, {name: require_sha256(value) for name, value in raw_hashes.items()}


def _verified_artifacts(
    path: Path, run_root: Path, hashes: dict[str, str]
) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    for name, digest in hashes.items():
        target = path.parent / name
        if not target.resolve().is_relative_to(run_root):
            raise ValueError("classification evidence path escapes run root")
        checked_bytes(target, digest)
        artifacts[target.relative_to(run_root).as_posix()] = digest
    artifacts[path.relative_to(run_root).as_posix()] = sha256(path.read_bytes())
    return artifacts


class LocalTargetClassificationEvidenceStore:
    """Store outside business rows; only a complete expected set may finalize."""

    def __init__(
        self,
        root: Path,
        *,
        mode: str = "shadow",
        snapshot_manifest_sha256: str,
        profile_sha256: str,
        normalization_version: str | None = None,
        rules_version: str | None = None,
        classification_schema_version: str | None = None,
        matching_policy_version: str | None = None,
        pipeline_name: str = "chembl_target",
    ) -> None:
        if mode not in {"shadow", "enrich"}:
            raise ValueError("evidence store needs shadow or enrich mode")
        self._root = root.resolve()
        self._mode = mode
        self._pipeline_name = pipeline_name
        self._snapshot_hash = require_sha256(snapshot_manifest_sha256)
        self._profile_hash = require_sha256(profile_sha256)
        self._versions = {
            "normalization_version": normalization_version,
            "rules_version": rules_version,
            "classification_schema_version": classification_schema_version,
            "matching_policy_version": matching_policy_version,
        }
        self._lock = RLock()

    def _run_root(self, run_id: str) -> Path:
        path = (self._root / _segment(run_id)).resolve()
        if not path.is_relative_to(self._root):
            raise ValueError("classification run path escapes artifact root")
        return path

    def publish_result(
        self,
        result: TargetClassificationResult,
        *,
        run_id: str,
        batch_id: str,
    ) -> TargetClassificationArtifactReference:
        with self._lock:
            run_root = self._run_root(run_id)
            row_root = _row_root(run_root, result, batch_id)
            manifest_path = row_root / "row-manifest.json"
            if (run_root / "manifest.json").exists() and not manifest_path.exists():
                raise ValueError("classification run is already finalized")
            validate_row_artifacts(
                result, run_id=run_id, profile_sha256=self._profile_hash
            )
            artifact_hashes = {
                artifact.name: sha256(artifact.payload) for artifact in result.artifacts
            }
            manifest = {
                "input_row_id": result.input_row_id,
                "run_id": run_id,
                "profile_sha256": self._profile_hash,
                "artifact_sha256": artifact_hashes,
            }
            payload = canonical_json_bytes(manifest)
            if manifest_path.exists() and manifest_path.read_bytes() != payload:
                raise ValueError("conflicting classification row retry")
            _publish_files(result, row_root, run_root)
            _write_same(manifest_path, payload)
            return TargetClassificationArtifactReference(
                manifest_path.as_uri(), sha256(payload)
            )

    def _collect_rows(
        self, run_root: Path, run_id: str
    ) -> tuple[set[str], dict[str, str]]:
        rows: dict[str, dict[str, str]] = {}
        artifacts: dict[str, str] = {}
        for path in sorted(run_root.glob("batches/*/rows/*/row-manifest.json")):
            row_id, hashes = _row_manifest(path, run_root, run_id, self._profile_hash)
            if row_id in rows and rows[row_id] != hashes:
                raise ValueError("conflicting duplicated classification row")
            rows[row_id] = hashes
            artifacts.update(_verified_artifacts(path, run_root, hashes))
        return set(rows), artifacts

    def finalize_run(
        self, *, run_id: str, expected_row_ids: tuple[str, ...]
    ) -> TargetClassificationArtifactReference:
        with self._lock:
            if len(expected_row_ids) != len(set(expected_row_ids)):
                raise ValueError("duplicate expected classification row identity")
            run_root = self._run_root(run_id)
            row_ids, artifacts = self._collect_rows(run_root, run_id)
            if row_ids != set(expected_row_ids):
                raise ValueError(
                    "classification evidence does not cover the expected rows"
                )
            manifest = {
                "artifact": "bioetl_iuphar_pipeline_evidence",
                "schema_version": 1,
                "pipeline_name": self._pipeline_name,
                "run_id": run_id,
                "mode": self._mode,
                "snapshot_manifest_sha256": self._snapshot_hash,
                "profile_sha256": self._profile_hash,
                "status": "complete",
                **self._versions,
                "row_count": len(row_ids),
                "input_row_ids": sorted(row_ids),
                "artifact_sha256": artifacts,
            }
            payload = canonical_json_bytes(manifest)
            path = run_root / "manifest.json"
            _write_same(path, payload)
            return TargetClassificationArtifactReference(path.as_uri(), sha256(payload))


__all__ = ["LocalTargetClassificationEvidenceStore"]
